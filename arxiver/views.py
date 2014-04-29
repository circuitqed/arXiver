__author__ = 'dave'

from datetime import datetime
import time
from flask import render_template, redirect, flash, session, url_for, request, g, jsonify
from flask.ext.login import login_user, logout_user, current_user, login_required
from arxiver import app, db, lm, oid, ARTICLES_PER_PAGE
from forms import LoginForm, SearchForm, FeedForm, SimpleSearchForm, EditForm
#from models import User, ROLE_USER, ROLE_ADMIN
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
    #print "load_user: ", u
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
        #flash('Login requested for OpenID="' + form.openid.data + '", remember_me=' + str(form.remember_me.data))

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
        articles=articles.paginate(page, ARTICLES_PER_PAGE, False)

        flash("Query time: %f s" % (time.time()-g.start_time))
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
    flash("Query time: %f s" % (time.time()-g.start_time))

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


#select author_id from articlesauthors, (select article_id as aid from articlesauthors where (author_id=6)) where (author_id=aid)
@app.route('/author/<int:id>')
@app.route('/author/<int:id>/page/<int:page>')
def author(id, page=1):
    author = Author.query.filter_by(id=id).first()
    if author == None:
        flash('Author #' + str(id) + ' not found.')
        return redirect(url_for('index'))

    author_articles = Article.query.filter(Article.authors.any(Author.id == author.id)).order_by(
        Article.created.desc()).paginate(page, ARTICLES_PER_PAGE, False)

    return render_template('author.html', author=author, similar_authors=author.similar_authors().limit(10),
                           articles=author_articles,
                           collaborators=author.collaborators().limit(10))


@app.route('/autocomplete/author/<search_term>')
def autocomplete_author(search_term):
    print 'autocomplete author'
    names = search_term.split(' ')
    conditions = []
    conditions.append(Author.lastname.ilike(names[-1] + '%'))
    if len(names) > 1:
        conditions.append(Author.forenames.ilike(search_term[0] + '%'))
    similar_authors = Author.query.filter(and_(*conditions)).limit(10).with_entities(Author.id, Author.forenames,
                                                                                     Author.lastname)
    alist = [{'id': a.id, 'forenames': a.forenames, 'lastname': a.lastname} for a in similar_authors]
    print alist

    return jsonify(authors=alist)


@app.route('/autocomplete/keyword/<search_term>')
def autocomplete_keyword(search_term):
    keywords = Keyword.query.filter(Keyword.keyword.ilike(search_term + '%')).limit(10)
    return jsonify(keywords=[{'id': k.id, 'keyword': k.keyword} for k in keywords])


@app.route('/feed/<id>', methods=['GET', 'POST'])
@app.route('/feed/<id>/page/<int:page>', methods=['GET', 'POST'])
@app.route('/feed/new', methods=['GET', 'POST'])
@login_required
def feed(id=None, page=1):
    if id is None:
        f = None
    else:
        f = Feed.query.filter(Feed.id == id).first()

    form = FeedForm()
    if form.validate_on_submit():
        print 'validated'
        if f is None:
            f = Feed()
            g.user.feeds.append(f)
            s = None
        else:
            s = Subscription.query.filter(and_(Subscription.feed_id == id, Subscription.user_id == g.user.id)).first()
        if s is None:
            s = Subscription(subscriber=g.user, feed=f)
        f = form.populate_obj(f)
        s.enable_email = form.enable_email.data
        s.email_frequency = form.email_frequency.data

        db.session.add(f)
        db.session.commit()
        flash('Feed updated.')
        return redirect(url_for('feed', id=f.id))
    else:
        form = FeedForm(request.form, f)
        if f is not None:
            articles = f.feed_articles().paginate(page, ARTICLES_PER_PAGE, False)
        else:
            articles = None
    return render_template('feed.html', feed=f, form=form, articles=articles)


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
    return render_template('edit.html', form=form)


@app.route('/about')
def about():
    return render_template('about.html')