__author__ = 'dave'

from datetime import datetime
import time
from flask import render_template, redirect, flash, session, url_for, request, g, jsonify
from flask.ext.login import login_user, logout_user, current_user, login_required
from arxiver import app, db, lm, oid, ARTICLES_PER_PAGE
from forms import LoginForm, SearchForm, FeedForm, SimpleSearchForm, EditForm, AuthorForm
# from models import User, ROLE_USER, ROLE_ADMIN
from models import *


@app.errorhandler(404)
def no_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


@lm.user_loader
def load_user(id):
    u = User.query.get(int(id))
    # print "load_user: ", u
    return u


@app.before_request
def before_request():
    g.user = current_user
    g.start_time = time.time()
    if g.user.is_authenticated():
        g.user.last_seen = datetime.datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()


@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        # flash('Login requested for OpenID="' + form.openid.data + '", remember_me=' + str(form.remember_me.data))

        return oid.try_login(form.openid.data, ask_for=['nickname', 'email', 'image', 'fullname', 'website'])

    return render_template('login.html',
                           title='Sign In',
                           form=form,
                           providers=app.config['OPENID_PROVIDERS'])


@oid.after_login
def after_login(resp):
    print resp.nickname, resp.email, resp.image, resp.fullname, resp.website
    if resp.email is None or resp.email == '':
        flash('Invalid login: email is missing! Please try again.')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == '':
            nickname = resp.email.split('@')[0]
        nickname = User.make_unique_nickname(nickname)
        user = User(nickname=nickname, email=resp.email, fullname=resp.fullname, role=ROLE_USER)
        db.session.add(user)
        db.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    if login_user(user, remember=remember_me):
        flash(user.nickname + ' logged in Successfully')
    return redirect(request.args.get('next') or url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
@app.route('/page/<int:page>', methods=['GET', 'POST'])
@app.route('/search/<string:query>', methods=['GET', 'POST'])
@app.route('/search/<string:query>/page/<int:page>', methods=['GET', 'POST'])
def index(page=1, query=None):
    start_time = time.time()
    articles = None
    if request.method == 'POST':
        return redirect(url_for('index', query=request.form['query']))
    if query is not None:
        print "running query"
        articles = Article.simple_search(query)
        print articles
        articles = articles.paginate(page, ARTICLES_PER_PAGE, False)

        flash("Query time: %f s" % (time.time() - g.start_time))
        print "query finished"
        return render_template('index.html', user=g.user, articles=articles)
    if g.user is not None and not g.user.is_anonymous():
        subscribed = False
        for s in g.user.subscriptions:
            subscribed = True
            articles = s.feed.feed_articles().paginate(page, ARTICLES_PER_PAGE, False)
        if not subscribed:
            print "Not subscribed"
            articles = Article.query.order_by(Article.created.desc()).paginate(page, ARTICLES_PER_PAGE, False)
    flash("Query time: %f s" % (time.time() - g.start_time))

    return render_template('index.html', user=g.user, articles=articles)


@app.route('/search/advanced', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    articles = None
    if form.validate_on_submit():
        conditions = []
        if form.title.data != '':
            conditions.append(Article.title.ilike('%' + form.title.data + '%'))
        if form.keyword.data != '':
            conditions.append(or_(Article.title.ilike('%' + form.keyword.data + '%'),
                                  Article.abstract.ilike('%' + form.keyword.data + '%')))
        if form.author.data != '':
            conditions.append(Article.authors.any(Author.lastname.ilike(form.author.data + "%")))
        if form.category.data != '':
            for cname in form.category.data:
                conditions.append(Category.name.ilike(cname + '%'))
        if conditions:
            articles = Article.query.filter(and_(*conditions))
    return render_template('search.html', form=form, articles=articles, navsearch=SimpleSearchForm())


@app.route('/article/<id>')
def article(id):
    a = Article.query.filter_by(id=id).first()
    if a is None:
        flash('Article #' + id + ' not found.')
        return redirect(url_for('index'))
    print a
    return render_template('article.html', article=a)


@app.route('/user/<nickname>')
@login_required
def user(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    if user == None:
        flash('User ' + nickname + ' not found.')
        return redirect(url_for('index'))
    return render_template('user.html', user=user)


# select author_id from articlesauthors, (select article_id as aid from articlesauthors where (author_id=6)) where (author_id=aid)
@app.route('/author/<int:id>')
@app.route('/author/<int:id>/page/<int:page>')
def author(id, page=1):
    author = Author.query.filter_by(id=id).first()
    if author == None:
        flash('Author #' + str(id) + ' not found.')
        return redirect(url_for('index'))

    author_articles = author.author_articles().paginate(page, ARTICLES_PER_PAGE, False)

    if g.user is not None:
        author_form = AuthorForm(user=g.user, author=author)
    else:
        author_form = None

    print author_form.feeds

    return render_template('author.html', author=author, similar_authors=author.similar_authors().limit(10),
                           articles=author_articles,
                           collaborators=author.collaborators().limit(10), author_form=author_form)


@app.route('/autocomplete/author/<search_term>')
def autocomplete_author(search_term):
    similar_authors = Author.auto_complete_authors(search_term).limit(10)
    alist = [{'id': a.id, 'forenames': a.forenames, 'lastname': a.lastname} for a in similar_authors]
    return jsonify(authors=alist)


@app.route('/add_author/<int:author_id>', methods=['GET', 'POST'])
def add_author(author_id):
    a = Author.query.filter(Author.id == author_id).first()
    form = AuthorForm(user=g.user, author=a)
    msg = "Success!"
    if not form.validate_on_submit():
        msg = '; '.join(form.errors.items())

    # update feeds
    for feed in Feed.query.filter(Feed.id.in_(form.feeds.data)):
        for sa_id, sa_name in form.similar_authors.choices:
            author = Author.query.filter(Author.id == int(sa_id)).first()
            if author in feed.authors:
                feed.authors.remove(author)
        for sa_id in form.similar_authors.data:
            author = Author.query.filter(Author.id == int(sa_id)).first()
            feed.authors.append(author)
        db.session.add(feed)
    db.session.commit()

    return msg


@app.route('/autocomplete/keyword/<search_term>')
def autocomplete_keyword(search_term):
    keywords = Keyword.query.filter(Keyword.keyword.ilike(search_term + '%')).limit(10)
    return jsonify(keywords=[{'id': k.id, 'keyword': k.keyword} for k in keywords])


@app.route('/feed/<int:id>', methods=['GET', 'POST'])
@app.route('/feed/<int:id>/page/<int:page>', methods=['GET', 'POST'])
@app.route('/feed/new', methods=['GET', 'POST'])
@login_required
def feed(id=None, page=1):
    if 'edit' in request.values:
        edit = True
    else:
        edit = False

    if id is None:
        f = Feed(name='New Feed')
        g.user.feeds.append(f)
        s = Subscription(subscriber=g.user, feed=f)
        db.session.add(f)
        db.session.add(s)
        db.session.commit()

        edit = True
    else:
        f = Feed.query.filter(Feed.id == id).first()
        s = Subscription.query.filter(and_(Subscription.feed_id == id, Subscription.user_id == g.user.id)).first()

    form = FeedForm(request.form, f, subscription=s)


    if form.validate_on_submit():
        edit = True
        if 'Delete' in request.values:
            if f is not None:
                # not sure if this is necessary (and will need to revise once it's possible to share feeds)
                for s in Subscription.query.filter(Subscription.feed_id == f.id):
                    db.session.delete(s)
                db.session.delete(f)
                db.session.commit()
                return redirect(url_for('index'))

        print 'validated'

        f = form.populate_obj(f)
        s.enable_email = form.enable_email.data
        s.email_frequency = form.email_frequency.data

        db.session.add(f)
        db.session.add(s)
        db.session.commit()
        flash('Feed updated.')
        return redirect(url_for('feed', id=f.id, edit=edit))
    else:
        if f is not None:
            articles = f.feed_articles().paginate(page, ARTICLES_PER_PAGE, False)
        else:
            articles = None
    return render_template('feed.html', feed=f, form=form, articles=articles, user=g.user, edit=edit)


@app.route('/add_feed_author', methods=['GET', 'POST'])
@login_required
def add_feed_author():
    similar_authors = None
    author = None

    if 'query' in request.values:
        similar_authors = Author.auto_complete_authors(request.values['query']).all()
        names = request.values['query'].split(' ')
        author = Author.query.filter(Author.lastname == names[-1]).filter(
            Author.forenames == ' '.join(names[:-1])).first()

    if 'author_id' in request.values:
        author = Author.query.filter(Author.id == request.values['author_id']).first()
        if author is not None:
            similar_authors = author.similar_authors()

    if 'feed_id' in request.values:
        feed_id = int(request.values['feed_id'])
    else:
        feed_id = None

    if author is None:
        author = Author.query.filter(Author.id == similar_authors[0].id).first()

    if similar_authors is None:
        return no_found_error("Error: author not found!")

    author_form = AuthorForm(user=g.user, author=author, feed_id=feed_id)

    return render_template('add_feed_author.html', author=author, similar_authors=similar_authors,
                           author_form=author_form, endpoint=request.values['endpoint'])


@app.route('/delete_feed_author', methods=['POST'])
@login_required
def delete_feed_author():
    # print request.values['author_id']
    # print request.values['feed_id']
    feed = Feed.query.filter(Feed.id == int(request.json['feed_id'])).first()
    author = Author.query.filter(Author.id == int(request.json['author_id'])).first()

    if (feed is None) or (author is None):
        print "Error: Invalid feed/author in delete_feed_author!"
        return "Error: Invalid feed/author in delete_feed_author!"

    if author in feed.authors:
        feed.authors.remove(author)
        db.session.add(feed)
        db.session.commit()

    return "Deleted author from feed."


@app.route('/delete_feed_keyword', methods=['POST'])
@login_required
def delete_feed_keyword():
    feed = Feed.query.filter(Feed.id == int(request.json['feed_id'])).first()
    keyword = Keyword.query.filter(Keyword.keyword.ilike(request.json['keyword'])).first()

    if (feed is None) or (keyword is None):
        print "Error: Invalid feed/keyword in delete_feed_keyword!"
        return "Error: Invalid feed/keyword in delete_feed_keyword!"

    if keyword in feed.keywords:
        feed.keywords.remove(keyword)
        db.session.add(feed)
        db.session.commit()

    return "Deleted author from feed."


@app.route('/add_feed_keyword', methods=['POST'])
@login_required
def add_feed_keyword():
    feed = Feed.query.filter(Feed.id == int(request.json['feed_id'])).first()
    keyword = Keyword.query.filter(Keyword.keyword.ilike(request.json['keyword'])).first()

    if keyword is None:
        keyword = Keyword(keyword=request.json['keyword'])
        db.session.add(keyword)
        db.session.commit()

    if (feed is None):
        print "Error: Invalid feed in delete_feed_keyword!"
        return "Error: Invalid feed in delete_feed_keyword!"

    if keyword not in feed.keywords:
        feed.keywords.append(keyword)
        db.session.add(feed)
        db.session.commit()

    return "Deleted author from feed."


@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    form = EditForm(g.user.nickname)
    if form.validate_on_submit():
        g.user.nickname = form.nickname.data
        g.user.fullname = form.fullname.data
        g.user.enable_email = form.enable_email.data
        g.user.email_frequency = form.email_frequency.data
        db.session.add(g.user)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit'))
    else:
        form.nickname.data = g.user.nickname
        form.fullname.data = g.user.fullname
    return render_template('edit.html', form=form, user=g.user)


@app.route('/about')
def about():
    return render_template('about.html')