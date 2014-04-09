__author__ = 'dave'

from datetime import datetime
from flask import render_template, redirect, flash, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from arxiver import app, db, lm, oid
from forms import LoginForm, SearchForm,FeedForm
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
    print "load_user: ", u
    return u


@app.before_request
def before_request():
    g.user = current_user
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
        flash(user.nickname + ' logged in Succesfully')
    return redirect(request.args.get('next') or url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
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
            conditions.append(Article.authors.any(Author.lastname.ilike(form.author.data)))
        if form.category.data != '':
            for cname in form.category.data:
                conditions.append(Category.name.ilike(cname + '%'))
        if conditions:
            articles = Article.query.filter(and_(*conditions))
    return render_template('index.html', form=form, articles=articles)


@app.route('/test')
def test():
    print [c.name for c in Category.query.all()]


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


@app.route('/author/<id>')
def author(id):
    author = Author.query.filter_by(id=id).first()
    if author == None:
        flash('Author #' + id + ' not found.')
        return redirect(url_for('index'))

    similar_authors = Author.query.filter(Author.lastname.ilike(author.lastname)).filter(
        Author.forenames.ilike(author.forenames[0] + '%'))

    return render_template('author.html', author=author, similar_authors=similar_authors)

@app.route('/feed/<id>')
@app.route('/feed/new')
@login_required
def feed(id=None):
    form=FeedForm()
    if id is None:
        feed=None
    else:
        feed=Feed.query.filter(Feed.id==id).first()
    for keyword in form.keywords:
        print keyword
    return render_template('feed.html',feed=feed, form=form)