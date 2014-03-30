__author__ = 'dave'

from hashlib import md5
from arxiver import db
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.associationproxy import association_proxy

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

feedcategories = db.Table('feedcategories',
                       db.Column('feed_id', db.Integer, db.ForeignKey('feed.id')),
                       db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)

articlescategories = db.Table('articlescategories',
                              db.Column('article_id', db.Integer, db.ForeignKey('article.id')),
                              db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)

usersubscriptions = db.Table('usersubscriptions',
                             db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                             db.Column('subscription_id',db.Integer,db.ForeignKey('subscription.id'))
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), index=True)
    nickname = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    role = db.Column(db.Integer, default=ROLE_USER)

    feeds = db.relationship('Subscription', secondary=usersubscriptions,
                            backref=db.backref('followers', lazy='dynamic'))


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    public = db.Column(db.Boolean, default=True)

    creator = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime)


    authors = db.relationship('Author', secondary=feedauthors,
                              backref=db.backref('authors', lazy='dynamic'))

    keywords = db.relationship('Keyword', secondary=feedkeywords,
                               backref=db.backref('feeds', lazy='dynamic'))

    categories = db.relationship('Category', secondary=feedcategories,
                               backref=db.backref('feeds', lazy='dynamic'))

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enable_email = db.Column(db.Boolean, default=False)
    email_frequency = db.Column(db.Integer, default=EFREQ_DAILY)

    feed_id =db.Column(db.Integer, db.ForeignKey('feed.id'))

class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    forenames = db.Column(db.String(120), index=True)
    lastname = db.Column(db.String(120), index=True)

#intermediate table used for ordering authors within articles
class ArticleAuthor(db.Model):
    __tablename__ = 'articlesauthors'

    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'), primary_key=True)
    position = db.Column(db.Integer)

    author = db.relationship('Author')

    def __init__(self,author):
        self.author=author

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

    #These set up the ordered list of authors
    _authors = db.relationship('ArticleAuthor',
        collection_class=ordering_list('position'))

    authors = association_proxy('_authors', 'author')

    categories = db.relationship('Category', secondary=articlescategories,
                                 backref=db.backref('articles', lazy='dynamic'))

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(120), index=True, unique=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)



