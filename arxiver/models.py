__author__ = 'dave'

from hashlib import md5
from arxiver import db
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy import or_, and_, func

# fulltext imports from http://sqlalchemy-searchable.readthedocs.org/en/latest/
from flask.ext.sqlalchemy import BaseQuery
from sqlalchemy_searchable import search, make_searchable, parse_search_query
from sqlalchemy_utils.types import TSVectorType
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import cast
from sqlalchemy.types import Interval
from sqlalchemy.orm import deferred
from flask.ext.login import UserMixin
# from social.apps.flask_app import models

import datetime

ROLE_USER = 0
ROLE_ADMIN = 1

EFREQ_DAILY = 0
EFREQ_WEEKLY = 1
EFREQ_MONTHLY = 2

feedkeywords = db.Table('feedkeywords',
                        db.Column('feed_id', db.Integer, db.ForeignKey('feed.id'), index=True),
                        db.Column('keyword_id', db.Integer, db.ForeignKey('keyword.id'), index=True)
)

feedauthors = db.Table('feedauthors',
                       db.Column('feed_id', db.Integer, db.ForeignKey('feed.id'), index=True),
                       db.Column('author_id', db.Integer, db.ForeignKey('author.id'), index=True)
)

feedcategories = db.Table('feedcategories',
                          db.Column('feed_id', db.Integer, db.ForeignKey('feed.id'), index=True),
                          db.Column('category_id', db.Integer, db.ForeignKey('category.id'), index=True)
)

articlescategories = db.Table('articlescategories'
                              '',
                              db.Column('article_id', db.Integer, db.ForeignKey('article.id'), index=True),
                              db.Column('category_id', db.Integer, db.ForeignKey('category.id'), index=True)
)

articlelikes = db.Table('articlelikes',
                        db.Column('article_id', db.Integer, db.ForeignKey('article.id'), index=True),
                        db.Column('user_id', db.Integer, db.ForeignKey('user.id'), index=True)
)

make_searchable()


class SearchQueryMixin(object):
    def search(self, search_query, vector=None, catalog=None):
        """
        Search given query with full text search.

        :param search_query: the search query
        """
        return search(self, search_query, vector=vector, catalog=catalog)


def as_dict(m):
    d = {}
    for c in m.__table__.columns:
        d[c.name] = getattr(m, c.name)
        if isinstance(d[c.name], datetime.date):
            d[c.name] = str(d[c.name])
    return d


class Synchronization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime(), index=True)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(), index=True)
    username = db.Column(db.String(200), index=True)
    nickname = db.Column(db.String(64), unique=True, index=True)
    password = db.Column(db.String(200))
    email = db.Column(db.String(), unique=True, index=True)
    active = db.Column(db.Boolean, default=True)
    role = db.Column(db.Integer, default=ROLE_USER)
    last_seen = db.Column(db.DateTime())
    enable_email = db.Column(db.Boolean)
    email_frequency = db.Column(db.Integer)

    subscriptions = db.relationship('Subscription', backref=db.backref('subscriber'), lazy='dynamic')

    feeds = db.relationship('Feed', backref=db.backref('owner'), lazy='dynamic')

    likes = db.relationship('Article', secondary=articlelikes,
                            backref=db.backref('likers', lazy='dynamic'))

    def avatar(self, size):
        return 'http://www.gravatar.com/avatar/' + md5(self.email).hexdigest() + '?d=mm&s=' + str(size)

    @staticmethod
    def make_unique_nickname(nickname):
        if User.query.filter_by(nickname=nickname).first() == None:
            return nickname
        version = 2
        while True:
            new_nickname = nickname + str(version)
            if User.query.filter_by(nickname=new_nickname).first() == None:
                break
            version += 1
        return new_nickname

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r>' % (self.username)


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    public = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)

    authors = db.relationship('Author', secondary=feedauthors,
                              backref=db.backref('authors', lazy='dynamic'))

    keywords = db.relationship('Keyword', secondary=feedkeywords,
                               backref=db.backref('feeds', lazy='dynamic'))

    categories = db.relationship('Category', secondary=feedcategories,
                                 backref=db.backref('feeds', lazy='dynamic'))

    subscriptions = db.relationship('Subscription', backref=db.backref('feed'), lazy='dynamic')


    def feed_articles(self):
        #explain (analyze,buffers) select * from article INNER JOIN (select id from article as blah where search_vector @@ to_tsquery('circuit:* & qed:* | qubit:*') union select article_id from articlesauthors as blah where author_id in (54962, 55738, 85464, 85465, 125598, 55921)) on id=blah order by created desc;
        #select * from (select distinct on (id) * from (select articles.* from articles where search_vector @@ ... union all select a.* from articles a join articlesauthors aa on ... where author_id = any (...)) s1) s2 order by created_at desc;
        #explain (analyze,buffers) select article.*, (article.id+0) as dummy_article_id from article where search_vector @@ to_tsquery('circuit:* & qed:* | qubit:*') union select a.*, (a.id+0) as dummy_article_id from article a join articlesauthors aa on a.id=aa.article_id where author_id in (54962, 55738, 85464, 85465, 125598, 55921) order by created desc;search_query = parse_search_query(' or '.join([kw.keyword for kw in self.keywords]))
        #select article.*, (article.id+0) as dummy_article_id from article where search_vector @@ to_tsquery('circuit:* & qed:* | qubit:*') union select a.*, (a.id+0) as dummy_article_id from article a join articlesauthors aa on a.id=aa.article_id where author_id in (54962, 55738, 85464, 85465, 125598, 55921) order by created desc;search_query = parse_search_query(' or '.join([kw.keyword for kw in self.keywords]))
        search_query = parse_search_query(' or '.join([kw.keyword for kw in self.keywords]))
        alist = [a.id for a in self.authors]
        s1 = select([ArticleAuthor.article_id]).where(ArticleAuthor.author_id.in_(alist))
        s2 = select([Article.id]).where(Article.search_vector.match_tsquery(search_query))
        q = Article.query.filter(Article.id.in_(s1.union(s2))).order_by((Article.created + cast("0",
                                                                                                Interval)).desc())  #The addition of the extra interval is important because it changes the way the query plan is computed and makes it run 100x faster!
        return q


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enable_email = db.Column(db.Boolean, default=False)
    email_frequency = db.Column(db.Integer, default=EFREQ_DAILY)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), index=True)

    # def __init__(self, id=None, subscriber=None, feed=None, enable_email=None,email_frequency=None):
    #     self.feed = feed
    #     self.subscriber = subscriber
    #     super(Subscription).__init__(self,id=id,enable_email=enable_email,email_frequency=email_frequency)


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    forenames = db.Column(db.String(), index=True)
    lastname = db.Column(db.String(), index=True)

    associations = db.relationship('ArticleAuthor', backref='author')
    articles = association_proxy('associations', 'article')

    def collaborators(self):
        articles_q = db.session.query(ArticleAuthor.article_id).filter_by(author_id=self.id).subquery()
        q = db.session.query(Author, func.count()).join(Author.associations).filter(
            ArticleAuthor.article_id.in_(articles_q), ArticleAuthor.author_id != self.id).group_by(Author.id).order_by(
            func.count().desc())
        return q

    def similar_authors(self):
        return Author.query.filter(Author.lastname.ilike(self.lastname),
                                   Author.forenames.ilike(self.forenames[0] + '%'), Author.id != self.id)

    @staticmethod
    def author_id_articles(id):
        return Article.query.filter(Article.authors.any(Author.id == id)).order_by(Article.created.desc())

    def author_articles(self):
        return Author.author_id_articles(self.id)

    @staticmethod
    def auto_complete_authors(search_term):
        names = search_term.split(' ')
        conditions = []
        conditions.append(Author.lastname.ilike(names[-1] + '%'))
        if len(names) > 1:
            conditions.append(Author.forenames.ilike(search_term[0] + '%'))
        similar_authors = Author.query.filter(and_(*conditions)).with_entities(Author.id, Author.forenames,
                                                                               Author.lastname)
        return similar_authors


    def __repr__(self):
        return self.forenames + ' ' + self.lastname


#intermediate table used for ordering authors within articles
class ArticleAuthor(db.Model):
    __tablename__ = 'articlesauthors'

    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), primary_key=True, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'), primary_key=True, index=True)
    position = db.Column(db.Integer)

    def __init__(self, author):
        self.author = author


class ArticleQuery(BaseQuery, SearchQueryMixin):
    pass


class Article(db.Model):
    query_class = ArticleQuery

    id = db.Column(db.Integer, primary_key=True)
    arxiv_id = db.Column(db.String(64), index=True, unique=True)
    title = db.Column(db.String(), index=True)
    abstract = db.Column(db.String())
    full_description = db.Column(db.String())
    comments = db.Column(db.String(), index=True)
    created = db.Column(db.Date(), index=True)
    updated = db.Column(db.Date(), index=True)
    doi = db.Column(db.String(), index=True)
    journalref = db.Column(db.String(), index=True)
    mscclass = db.Column(db.String(), index=True)
    acmclass = db.Column(db.String(), index=True)
    license = db.Column(db.String(), index=True)

    title_search_vector = deferred(db.Column(TSVectorType('title')))
    abstract_search_vector = deferred(db.Column(TSVectorType('abstract')))
    title_abstract_search_vector = deferred(db.Column(TSVectorType('title', 'abstract')))
    search_vector = deferred(db.Column(TSVectorType('full_description')))

    #These set up the ordered list of authors
    associations = db.relationship('ArticleAuthor',
                                   collection_class=ordering_list('position'),
                                   backref='article'
    )

    authors = association_proxy('associations', 'author')

    categories = db.relationship('Category', secondary=articlescategories,
                                 backref=db.backref('articles', lazy='dynamic'))

    @staticmethod
    def simple_search(query):
        q1 = Article.query.filter(Article.search_vector.match_tsquery(parse_search_query(query)))
        #q2 = Article.query.filter(Article.authors.any(Author.lastname.ilike(query)))
        #q2 = Article.query.filter(Article.authors.any(func.lower(Author.lastname) == func.lower(query)))

        #q = q1.union(q2)

        return q1.order_by((Article.created + cast("0", Interval)).desc())
        #return q1.order_by(Article.created.desc())


    def __repr__(self):
        return self.title


class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(120), index=True, unique=True)


    @staticmethod
    def auto_complete_keyword(search_term):
        return Keyword.query.filter(Keyword.keyword.ilike(search_term) + '%')

    def __repr__(self):
        return self.keyword


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, index=True)

    def __repr__(self):
        return self.name


