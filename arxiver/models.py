__author__ = 'dave'

from hashlib import md5
from arxiver import db
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.associationproxy import association_proxy
import datetime

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
                             db.Column('subscription_id', db.Integer, db.ForeignKey('subscription.id'))
)

articlelikes = db.Table('articlelikes',
                        db.Column('article_id', db.Integer, db.ForeignKey('article.id')),
                        db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

def as_dict(m):
    d={}
    for c in m.__table__.columns:
        d[c.name]=getattr(m, c.name)
        if isinstance(d[c.name], datetime.date):
            d[c.name]=str(d[c.name])
    return d

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), index=True)
    nickname = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    role = db.Column(db.Integer, default=ROLE_USER)

    feeds = db.relationship('Subscription', secondary=usersubscriptions,
                            backref=db.backref('followers', lazy='dynamic'))

    likes = db.relationship('Article', secondary=articlelikes,
                            backref=db.backref('likers', lazy='dynamic'))

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

    def feed_articles(self):
        conditions=[]
        for a in f.authors:
            conditions.append(Article.authors.has(Author.id==a.id))
        for kw in f.keywords:
            conditions.append(Article.title.ilike('%'+kw+'%'))
            conditions.append(Article.abstract.ilike('%'+kw+'%'))

        q = Article.query.filter(or_(*conditions))
        return q


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enable_email = db.Column(db.Boolean, default=False)
    email_frequency = db.Column(db.Integer, default=EFREQ_DAILY)

    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'))


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    forenames = db.Column(db.String(120), index=True)
    lastname = db.Column(db.String(120), index=True)

    associations = db.relationship('ArticleAuthor', backref='author')
    articles = association_proxy('associations', 'article')


#intermediate table used for ordering authors within articles
class ArticleAuthor(db.Model):
    __tablename__ = 'articlesauthors'

    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'), primary_key=True)
    position = db.Column(db.Integer)

    def __init__(self, author):
        self.author = author


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
    associations = db.relationship('ArticleAuthor',
                                   collection_class=ordering_list('position'),
                                   backref='article'
    )

    authors = association_proxy('associations', 'author')

    categories = db.relationship('Category', secondary=articlescategories,
                                 backref=db.backref('articles', lazy='dynamic'))

    def __repr__(self):
        return self.title


class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(120), index=True, unique=True)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)



