__author__ = 'dave'

# Module, not the class: every use in this file is datetime.datetime.*, and
# the old `from datetime import datetime` only worked because the star
# import of .models further down happened to rebind the name to the
# module. Anything at module scope ran before that and broke.
import datetime
import time
import secrets
from flask import render_template, redirect, flash, session, url_for, request, g, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy.exc import IntegrityError
from arxiver import app, db, lm, ARTICLES_PER_PAGE, magiclink, harvest_state

from .forms import (LoginForm, SearchForm, FeedForm, SimpleSearchForm, EditForm,
                    AuthorForm, MagicLinkForm)
from .models import *


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
#    with open('/home/dave/arXiver/tmp/test.txt','a') as f:
#        f.write(dir(g.user))
    if g.user.is_authenticated:
        g.user.last_seen = datetime.datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()


@app.after_request
def after_request(response):
    diff = int((time.time() - g.start_time) * 1000)  # to get a time in ms

    if (response.response and response.content_type.startswith("text/html") and response.status_code == 200):
        response.response[0] = response.response[0].replace(b'__EXECUTION_TIME__', str(diff).encode())
        response.headers["content-length"] = len(response.response[0])
    return response


@app.teardown_appcontext
def commit_on_success(error=None):
    if error is None:
        db.session.commit()


@app.teardown_request
def shutdown_session(exception=None):
    db.session.remove()


@app.context_processor
def inject_user():
    try:
        return {'user': g.user}
    except AttributeError:
        return {'user': None}


def _allowed_to_sign_in(email):
    """Check the address against SIGNIN_ALLOWLIST. Empty list lets anyone in."""
    raw = (app.config.get('SIGNIN_ALLOWLIST') or '').strip()
    if not raw:
        return True
    domain = email.rsplit('@', 1)[-1]
    for entry in raw.split(','):
        entry = entry.strip().lower()
        if not entry:
            continue
        if entry == email or entry == domain or entry == '@' + domain:
            return True
    return False


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Ask for an email address and mail a sign-in link to it."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # FlaskForm purely for its CSRF token: without one, any page could make a
    # visitor's browser POST here, mailing a link to an address of the
    # attacker's choosing and burning the visitor's IP against the rate limit.
    form = MagicLinkForm()
    next_url = magiclink.safe_next(request.args.get('next'))

    if form.validate_on_submit():
        email = magiclink.normalize_email(form.email.data)
        next_url = magiclink.safe_next(request.form.get('next')) or next_url
        if not magiclink.valid_email(email):
            flash("That doesn't look like an email address.")
            return render_template('login.html', title='Sign In', form=form,
                                   email=form.email.data, next=next_url)

        ip = magiclink.client_ip(request)
        # Everything below reports the same outcome to the browser. A
        # rate-limited address, one that isn't on the allowlist, and a
        # fresh one all look identical, so the form can't be used to
        # enumerate who has an account here.
        if _allowed_to_sign_in(email) and not magiclink.rate_limited(email, ip):
            magiclink.issue(email, ip, next_url)
        else:
            app.logger.info('sign-in link withheld for %s from %s', email, ip)
        try:
            magiclink.purge_expired()
        except Exception:
            app.logger.exception('auth token purge failed')
        return render_template('login_sent.html', title='Check Your Email', email=email)

    if request.method == 'POST':
        # Only reachable on a stale or missing CSRF token -- the form has no
        # other validators.
        flash('That form had expired. Please try again.')

    return render_template('login.html', title='Sign In', form=form,
                           email='', next=next_url)


@app.route('/login2')
def login2():
    """Old Google sign-in path -- keep it alive for stale bookmarks."""
    return redirect(url_for('login'))


@app.route('/auth/verify')
def verify():
    """Redeem a magic link: sign the user in, creating the account if new."""
    email, next_url = magiclink.consume(request.args.get('token'))
    if email is None:
        flash('That sign-in link has expired or was already used. Here is a fresh start.')
        return redirect(url_for('login'))

    user = User.query.filter(func.lower(User.email) == email).first()
    if user is None:
        user = User(email=email,
                    fullname=email.split('@')[0],
                    nickname=User.make_unique_nickname(email.split('@')[0]),
                    active=True,
                    role=ROLE_USER)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            # Two clicks landing together both miss the SELECT and both
            # insert; the loser trips the unique index on email. That is
            # a successful sign-in, not an error -- read back the winner.
            db.session.rollback()
            user = User.query.filter(func.lower(User.email) == email).first()
            if user is None:
                flash('Could not complete sign in. Please request a new link.')
                return redirect(url_for('login'))

    if not login_user(user, remember=True):
        # Deactivated account -- the link was valid, so say so plainly
        # rather than redirecting to a login page that will keep working
        # and keep failing.
        app.logger.info('sign-in refused for deactivated account %s', user.email)
        flash('That account has been deactivated. Get in touch if that is a surprise.')
        return redirect(url_for('index'))
    flash('Signed in as ' + user.email)
    return redirect(next_url or url_for('index'))


@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    flash('Signed out.')
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
@app.route('/page/<int:page>', methods=['GET', 'POST'])
@app.route('/search/<string:query>', methods=['GET', 'POST'])
@app.route('/search/<string:query>/page/<int:page>', methods=['GET', 'POST'])
def index(page=1, query=None):
    articles = None
    if request.method == 'POST':
        return redirect(url_for('index', query=request.form['query']))
    if query is not None:
        articles = Article.simple_search(query)
        articles = articles.paginate(page=page, per_page=ARTICLES_PER_PAGE, error_out=False)

        return render_template('index.html', user=g.user, articles=articles)
    if g.user is not None and not g.user.is_anonymous:
        subscribed = False
        for s in g.user.subscriptions:
            subscribed = True
            articles = s.feed.feed_articles().paginate(page=page, per_page=ARTICLES_PER_PAGE, error_out=False)
        if not subscribed:
            articles = Article.query.order_by(Article.created.desc()).paginate(page=page, per_page=ARTICLES_PER_PAGE, error_out=False)
    else:
        articles = Article.query.order_by(Article.created.desc()).paginate(page=page, per_page=ARTICLES_PER_PAGE, error_out=False)

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
    print(a)
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

    author_articles = author.author_articles().paginate(page=page, per_page=ARTICLES_PER_PAGE, error_out=False)

    # if g.user is not None and g.user.is_authenticated():
    #     author_form = AuthorForm(user=g.user, author=author)
    # else:
    #     author_form = None

    return render_template('author.html', author=author, similar_authors=author.similar_authors().limit(10),
                           articles=author_articles,
                           collaborators=author.collaborators().limit(10))  #, author_form=author_form)


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
        msg = '; '.join(list(form.errors.items()))

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


def _feed_for_write(feed_id):
    """Return a feed the signed-in user owns, or abort.

    Every feed-mutating endpoint looked its feed up by the id in the request
    body and checked only that the caller was logged in -- so any account
    could edit or delete any other account's feeds. Sign-up is now open to
    anyone who can receive an email, which makes that a much shorter path
    than it was when login required a Google account. 404 rather than 403 so
    the reply doesn't confirm which feed ids exist.
    """
    try:
        feed_id = int(feed_id)
    except (TypeError, ValueError):
        abort(404)
    feed = Feed.query.filter(Feed.id == feed_id).first()
    if feed is None or feed.owner_id != current_user.id:
        abort(404)
    return feed


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
        return redirect(url_for('feed', id=f.id, edit=True))
    else:
        f = Feed.query.filter(Feed.id == id).first()
        if f is None:
            abort(404)
        owns = f.owner_id == current_user.id
        # The `public` column was written by the form and then never read, so
        # every feed was visible to every signed-in account and -- worse --
        # the Delete branch below would delete any of them. Reads now need
        # ownership or a public feed; writes always need ownership.
        if request.method == 'POST' and not owns:
            abort(404)
        if not owns and not f.public:
            abort(404)
        s = Subscription.query.filter(and_(Subscription.feed_id == id,
                                           Subscription.user_id == current_user.id)).first()

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

        print('validated')

        f = form.populate_obj(f)
        if s is None:
            # An owner with no subscription row (possible for feeds whose
            # duplicate subscription was dropped during the account merge)
            # would otherwise 500 here.
            s = Subscription(subscriber=current_user, feed=f)
        s.enable_email = form.enable_email.data
        s.email_frequency = form.email_frequency.data

        db.session.add(f)
        db.session.add(s)
        db.session.commit()
        flash('Feed updated.')
        return redirect(url_for('feed', id=f.id, edit=edit))
    else:
        if f is not None:
            articles = f.feed_articles().paginate(page=page, per_page=ARTICLES_PER_PAGE, error_out=False)
            if articles.total == 0: edit = True
            if form.subscription is not None:
                form.enable_email.data = form.subscription.enable_email
                form.email_frequency.data = form.subscription.email_frequency
        else:
            articles = None
            edit = True

    if f is not None:
        feed_authors = f.authors.order_by(Author.lastname)
    return render_template('feed.html', feed=f, form=form, articles=articles, feed_authors=feed_authors, user=g.user,
                           edit=edit)


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
    feed = _feed_for_write(request.json.get('feed_id'))
    author = Author.query.filter(Author.id == request.json.get('author_id')).first()

    if author is None:
        return "Error: Invalid author in delete_feed_author!", 400

    if author in feed.authors:
        feed.authors.remove(author)
        db.session.add(feed)
        db.session.commit()

    return "Deleted author from feed."


@app.route('/delete_feed_keyword', methods=['POST'])
@login_required
def delete_feed_keyword():
    feed = _feed_for_write(request.json.get('feed_id'))
    keyword = Keyword.query.filter(Keyword.keyword.ilike(request.json.get('keyword') or '')).first()

    if keyword is None:
        return "Error: Invalid keyword in delete_feed_keyword!", 400

    if keyword in feed.keywords:
        feed.keywords.remove(keyword)
        db.session.add(feed)
        db.session.commit()

    return "Deleted author from feed."


@app.route('/add_feed_keyword', methods=['POST'])
@login_required
def add_feed_keyword():
    feed = _feed_for_write(request.json.get('feed_id'))
    raw = (request.json.get('keyword') or '').strip()
    if not raw:
        return "Error: Missing keyword in add_feed_keyword!", 400
    keyword = Keyword.query.filter(Keyword.keyword.ilike(raw)).first()

    if keyword is None:
        keyword = Keyword(keyword=raw)
        db.session.add(keyword)
        db.session.commit()

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


@app.route('/update')
@app.route('/update/<string:cmd>')
def update(cmd=''):
    # Header first so the token can stay out of request URLs, which get
    # logged by every proxy in front of this app; the query parameter stays
    # supported for existing callers. compare_digest rather than != so the
    # check doesn't leak the token's prefix through timing.
    expected = app.config.get('UPDATE_TOKEN', '')
    token = request.headers.get('X-Update-Token') or request.args.get('token', '')
    if not expected or not token or not secrets.compare_digest(token, expected):
        abort(403)
    if cmd == 'status':
        # `stale` says whether a 'running' claim is one the next harvest would
        # take over, so a wedged claim is visible without reading the file.
        return jsonify(harvest_state.status())
    # Triggering a harvest over HTTP is gone. It ran the harvest as a thread
    # in a gunicorn worker, which starved request handling badly enough to
    # serve white pages during a long catch-up. Harvests now run in their own
    # process, on a schedule, from the cron container.
    return ('harvests are no longer started over HTTP -- they run in their own '
            'process.\n'
            'scheduled:  daily at HARVEST_AT (default 08:15 UTC) in the cron container\n'
            'manually:   docker compose run --rm --no-deps cron python harvest.py\n'
            'full walk:  docker compose run --rm --no-deps cron python harvest.py --all\n'
            'status:     /update/status\n'), 410
