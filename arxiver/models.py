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

    authors = db.relationship('Author', secondary=feedauthors,
                               backref=db.backref('authors', lazy='dynamic'))

    keywords = db.relationship('Keyword', secondary=feedkeywords,
                               backref=db.backref('feeds', lazy='dynamic'))

class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(120), index=True)
    lastname = db.Column(db.String(120), index=True)
    middlename = db.Column(db.String(120), default='', index=True)


class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(120), index=True, unique=True)





