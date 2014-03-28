__author__ = 'dave'

from hashlib import md5
from arxiver import db

ROLE_USER = 0
ROLE_ADMIN = 1

EFREQ_DAILY = 0
EFREQ_WEEKLY = 1
EFREQ_MONTHLY = 2

feedkeywords = db.Table('feedkeywords',
                        db.Column('feed_id', db.Integer, db.ForeignKey('feed.id')),
                        db.Column('keyword_id', db.Integer, db.ForeignKey('keyword.id'))
)

feedauthors = db.Table('feedauthors',
                       db.Column('feed_id', db.Integer, db.ForeignKey('feed.id')),
                       db.Column('author_id', db.Integer, db.ForeignKey('author.id'))
)

articlesauthors = db.Table('articlesauthors',
                           db.Column('article_id', db.Integer, db.ForeignKey('article.id')),
                           db.Column('author_id', db.Integer, db.ForeignKey('author.id'))
)

articlescategories = db.Table('articlescategories',
                              db.Column('article_id', db.Integer, db.ForeignKey('article.id')),
                              db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), index=True)
    nickname = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    role = db.Column(db.Integer, default=ROLE_USER)
    feeds = db.relationship('Feed', backref='user', lazy='dynamic')


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feedname = db.Column(db.String(120), index=True)
    enable_email = db.Column(db.Boolean, default=False)
    email_frequency = db.Column(db.Integer, default=EFREQ_DAILY)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    authors = db.relationship('Author', secondary=feedauthors,
                              backref=db.backref('authors', lazy='dynamic'))

    keywords = db.relationship('Keyword', secondary=feedkeywords,
                               backref=db.backref('feeds', lazy='dynamic'))


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    forenames = db.Column(db.String(120), index=True)
    lastname = db.Column(db.String(120), index=True)


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    arxiv_id = db.Column(db.String(64), index=True, unique=True)
    title = db.Column(db.String(120))
    abstract = db.Column(db.String(2000), index=True)
    comments = db.Column(db.String(120))
    created = db.Column(db.Date(), index=True)
    updated = db.Column(db.Date(), index=True)
    doi = db.Column(db.String(120), index=True)
    journalref = db.Column(db.String(120), index=True)
    mscclass = db.Column(db.String(120))
    acmclass = db.Column(db.String(120))
    license = db.Column(db.String(120))

    authors = db.relationship('Author', secondary=articlesauthors,
                              backref=db.backref('articles', lazy='dynamic'))

    categories = db.relationship('Category', secondary=articlescategories,
                                 backref=db.backref('articles', lazy='dynamic'))

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(120), index=True, unique=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)



