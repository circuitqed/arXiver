__author__ = 'dave'

from arxiver import db
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy import or_, and_, func
import sqlalchemy

# fulltext imports from http://sqlalchemy-searchable.readthedocs.org/en/latest/
from flask_sqlalchemy.query import Query as BaseQuery
from sqlalchemy_searchable import search, make_searchable
from sqlalchemy_utils.types import TSVectorType
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import cast
from sqlalchemy.types import Interval


def like_escape(value):
    """Escape LIKE/ILIKE metacharacters in a value used as a literal.

    These names come from arXiv metadata and from URLs, and ILIKE treats
    backslash as an escape character -- so an author genuinely named "Bele\\"
    made similar_authors() raise InvalidEscapeSequence and return a 500. The
    same applies to % and _, which would silently turn a name into a wildcard.
    """
    return (value or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def parse_search_query(query):
    """Convert a human search query to PostgreSQL tsquery format.

    Compatibility shim for the older sqlalchemy_searchable API. Adjacent
    terms get an implicit &; 'or' maps to |, 'and' maps to &.

    The result is passed to to_tsquery() as a bound parameter, so this is not
    an injection boundary -- but it IS a syntax boundary. to_tsquery() raises
    on a malformed query, and a raised error here is a 500 on a public page:
    searching for the single word "or" used to emit the bare query "|" and
    blow up. So every term is reduced to characters tsquery accepts and the
    operator structure is normalised -- no leading, trailing or doubled
    operators -- returning '' (which to_tsquery accepts, matching nothing)
    rather than a fragment.
    """
    result = []
    for token in query.split():
        lower = token.lower()
        if lower in ('or', '|'):
            op = '|'
        elif lower in ('and', '&'):
            op = '&'
        else:
            op = None

        if op is not None:
            # Drop an operator with nothing to its left and collapse runs of
            # them, so "or qubit" and "a or and b" stay parseable.
            if result and result[-1] not in ('|', '&'):
                result.append(op)
            continue

        # Keep only what tsquery treats as part of a lexeme. Quotes, colons,
        # parens, backslashes and '*' are syntax to its parser, so stripping
        # them is what keeps a query like it's or (foo) from erroring. The
        # old code doubled single quotes, which was both unnecessary (bound
        # parameter) and the cause of a second syntax error: a term of only
        # quotes became "''" and then "'':*".
        term = ''.join(ch for ch in token if ch.isalnum() or ch in '-_')
        if not term:
            continue
        if result and result[-1] not in ('|', '&'):
            result.append('&')
        result.append(term + ':*')

    # A trailing operator is a syntax error on its own.
    while result and result[-1] in ('|', '&'):
        result.pop()
    return ' '.join(result)
from sqlalchemy.orm import deferred
from flask_login import UserMixin
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

make_searchable(db.metadata)

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
    avatar = db.Column(db.String())
    enable_email = db.Column(db.Boolean)
    email_frequency = db.Column(db.Integer)

    subscriptions = db.relationship('Subscription', backref=db.backref('subscriber'), lazy='dynamic')

    feeds = db.relationship('Feed', backref=db.backref('owner'), lazy='dynamic')

    likes = db.relationship('Article', secondary=articlelikes,
                            backref=db.backref('likers', lazy='dynamic'))

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

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        # Rows predating the magic-link switch have active IS NULL, and a
        # None here makes Flask-Login refuse the sign-in without saying
        # why. Only an explicit False deactivates an account.
        return self.active is not False

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return '<User %r>' % (self.username)


class AuthToken(db.Model):
    """A pending magic-link sign-in.

    The raw token only ever exists in the emailed URL; we store its
    SHA-256 hash, so a database leak doesn't hand out live links.
    Rows are kept after use (used_at set) as a short audit trail and
    swept by ``purge_expired``.
    """
    __tablename__ = 'auth_token'

    token_hash = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(), nullable=False, index=True)
    created = db.Column(db.DateTime(), nullable=False, default=datetime.datetime.utcnow)
    expires = db.Column(db.DateTime(), nullable=False, index=True)
    used_at = db.Column(db.DateTime())
    # IP that asked for the link -- rate limiting and abuse debugging.
    requester_ip = db.Column(db.String(64))
    # Where to drop the user after a successful verify. Always a
    # relative path; validated before it is stored.
    next_url = db.Column(db.String())

    def __repr__(self):
        return '<AuthToken %r %s>' % (self.email, self.token_hash[:8])


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    public = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)

    authors = db.relationship('Author', secondary=feedauthors, lazy='dynamic',
                              backref=db.backref('authors', lazy='dynamic'))

    keywords = db.relationship('Keyword', secondary=feedkeywords,
                               backref=db.backref('feeds', lazy='dynamic'))

    categories = db.relationship('Category', secondary=feedcategories,
                                 backref=db.backref('feeds', lazy='dynamic'))

    subscriptions = db.relationship('Subscription', backref=db.backref('feed'), lazy='dynamic')


    def feed_articles(self):
        # explain (analyze,buffers) select * from article INNER JOIN (select id from article as blah where search_vector @@ to_tsquery('circuit:* & qed:* | qubit:*') union select article_id from articlesauthors as blah where author_id in (54962, 55738, 85464, 85465, 125598, 55921)) on id=blah order by created desc;
        #select * from (select distinct on (id) * from (select articles.* from articles where search_vector @@ ... union all select a.* from articles a join articlesauthors aa on ... where author_id = any (...)) s1) s2 order by created_at desc;
        #explain (analyze,buffers) select article.*, (article.id+0) as dummy_article_id from article where search_vector @@ to_tsquery('circuit:* & qed:* | qubit:*') union select a.*, (a.id+0) as dummy_article_id from article a join articlesauthors aa on a.id=aa.article_id where author_id in (54962, 55738, 85464, 85465, 125598, 55921) order by created desc;search_query = parse_search_query(' or '.join([kw.keyword for kw in self.keywords]))
        #select article.*, (article.id+0) as dummy_article_id from article where search_vector @@ to_tsquery('circuit:* & qed:* | qubit:*') union select a.*, (a.id+0) as dummy_article_id from article a join articlesauthors aa on a.id=aa.article_id where author_id in (54962, 55738, 85464, 85465, 125598, 55921) order by created desc;search_query = parse_search_query(' or '.join([kw.keyword for kw in self.keywords]))
        #search_query = parse_search_query(' or '.join([kw.keyword for kw in self.keywords]))
        q = Article.query.filter(Article.id.in_(self.article_id_union(distinct=False)))
        return q.order_by((Article.created + cast("0",
                                                  Interval)).desc())  # Deliberately non-indexable sort key -- see the note in simple_search for why, and what the measurements are.

    def article_id_union(self, distinct=True):
        """Article ids matching this feed: its authors' papers, plus keyword hits.

        `distinct` picks UNION over UNION ALL. For feed_articles it can be
        False -- the enclosing IN (...) dedupes anyway, and skipping the
        HashAggregate is worth about 20% of the query. Anything that counts
        these rows needs True, because an article matching both an author and
        a keyword appears twice otherwise (18,521 vs 15,257 on feed 3).
        """
        search_query = parse_search_query(' or '.join([kw.keyword for kw in self.keywords]))
        alist = [a.id for a in self.authors]
        s1 = select([ArticleAuthor.article_id]).where(ArticleAuthor.author_id.in_(alist))
        s2 = select([Article.id]).where(Article.search_vector.op('@@')(func.to_tsquery(search_query)))
        return s1.union(s2) if distinct else s1.union_all(s2)

    def feed_article_count(self):
        """How many articles this feed matches.

        Counted straight off the union rather than by wrapping
        feed_articles(). Letting paginate() count meant re-scanning `article`
        for rows the union had already identified, and its subquery selected
        every column including search_vector: 480ms, against 156ms for this.
        """
        return db.session.execute(
            select([func.count()]).select_from(self.article_id_union().alias())).scalar()


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enable_email = db.Column(db.Boolean, default=False)
    email_frequency = db.Column(db.Integer, default=EFREQ_DAILY)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), index=True)

    # def __init__(self, id=None, subscriber=None, feed=None, enable_email=None,email_frequency=None):
    # self.feed = feed
    #     self.subscriber = subscriber
    #     super(Subscription).__init__(self,id=id,enable_email=enable_email,email_frequency=email_frequency)


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    forenames = db.Column(db.String(), index=True)
    lastname = db.Column(db.String(), index=True)

    associations = db.relationship('ArticleAuthor',
                                   backref=db.backref('author', lazy='joined'))
    articles = association_proxy('associations', 'article')

    def collaborators(self):
        articles_q = db.session.query(ArticleAuthor.article_id).filter_by(author_id=self.id).subquery()
        q = db.session.query(Author, func.count()).join(Author.associations).filter(
            ArticleAuthor.article_id.in_(articles_q), ArticleAuthor.author_id != self.id).group_by(Author.id).order_by(
            func.count().desc())
        return q

    def similar_authors(self):
        conditions = [Author.lastname.ilike(like_escape(self.lastname)),
                      Author.id != self.id]
        if self.forenames:
            conditions.append(Author.forenames.ilike(like_escape(self.forenames[0]) + '%'))
        return Author.query.filter(*conditions)

    @staticmethod
    def author_id_articles(id):
        return Article.query.filter(Article.authors.any(Author.id == id)).order_by(Article.created.desc())

    def author_articles(self):
        return Author.author_id_articles(self.id)

    def article_count(self):
        """How many articles this author has.

        An index lookup on articlesauthors, rather than letting paginate()
        count a subquery over `article` -- same number, far less work, and
        /author/ is both the most crawled route here and the one where a
        prolific author made the count expensive.
        """
        return db.session.execute(
            select([func.count()]).select_from(ArticleAuthor.__table__)
            .where(ArticleAuthor.author_id == self.id)).scalar()

    @staticmethod
    def auto_complete_authors(search_term):
        names = search_term.split(' ')
        conditions = []
        conditions.append(Author.lastname.ilike(like_escape(names[-1]) + '%'))
        if len(names) > 1 and search_term:
            conditions.append(Author.forenames.ilike(like_escape(search_term[0]) + '%'))
        similar_authors = Author.query.filter(and_(*conditions)).with_entities(Author.id, Author.forenames,
                                                                               Author.lastname)
        return similar_authors


    def __repr__(self):
        return self.forenames + ' ' + self.lastname


# intermediate table used for ordering authors within articles
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
    # index=True was on nearly every column here as a just-in-case. Postgres
    # has never used any of them: pg_stat_user_indexes showed 0 scans for
    # title, comments, doi, journalref, mscclass, acmclass and license across
    # billions of pkey lookups, while they cost 1069 MB of disk and a write on
    # every harvested row. Indexes kept below are the ones with measured
    # scans: arxiv_id (the harvest's lookup), created and updated (ordering).
    arxiv_id = db.Column(db.String(64), index=True, unique=True)
    title = db.Column(db.String())
    abstract = db.Column(db.String())
    full_description = db.Column(db.String())
    comments = db.Column(db.String())
    created = db.Column(db.Date(), index=True)
    updated = db.Column(db.Date(), index=True)
    doi = db.Column(db.String())
    journalref = db.Column(db.String())
    mscclass = db.Column(db.String())
    acmclass = db.Column(db.String())
    license = db.Column(db.String())

    # Only this one is ever queried. There were three more -- over title,
    # abstract, and title+abstract -- left from comparing full-text
    # approaches; they were never referenced again, but each carried a GIN
    # index and a trigger recomputing to_tsvector on every harvested row.
    search_vector = deferred(db.Column(TSVectorType('full_description')))

    #These set up the ordered list of authors
    # selectin: one extra query fetches the associations for every article in
    # the page at once, instead of one per article. Every template that lists
    # articles walks article.authors, so this belongs on the relationship
    # rather than on each query that happens to remember to ask for it.
    associations = db.relationship('ArticleAuthor', order_by="ArticleAuthor.position",
                                   collection_class=ordering_list('position'),
                                   backref='article', lazy='selectin'
    )

    authors = association_proxy('associations', 'author')

    categories = db.relationship('Category', secondary=articlescategories,
                                 backref=db.backref('articles', lazy='dynamic'))

    @staticmethod
    def simple_search(query):
        #q= db.session.query(Article)
        #q1= search(q,query, vector=Article.search_vector)
        q1 = Article.query.filter(Article.search_vector.op('@@')(func.to_tsquery(parse_search_query(query))))
        #q1 = Article.query.filter(Article.search_vector.match(sqlalchemy.func.tsqparse(query)))
        #q2 = Article.query.filter(Article.authors.any(Author.lastname.ilike(query)))
        #q2 = Article.query.filter(Article.authors.any(func.lower(Author.lastname) == func.lower(query)))

        #q = q1.union(q2)

        # Do not "clean up" the + interval '0'. It makes the sort key a
        # non-indexable expression on purpose, which forces the planner to
        # resolve the full-text filter through the GIN index and then top-N
        # sort the matches. The commented-out plain ORDER BY below reads
        # better and is a trap: it lets the planner walk ix_article_created
        # backwards hoping to hit 10 matches early. Measured on 3.1M rows:
        #
        #   term            plain ORDER BY     with + interval '0'
        #   qubit:*                   8 ms                  333 ms
        #   fluxonium:*           10,221 ms                    7 ms
        #   (no matches)       did not finish                  7 ms
        #
        # Postgres cannot estimate prefix-match (:*) selectivity well, so for
        # anything rare it picks the date walk and scans most of the table.
        # The hack trades a bounded ~300 ms for an unbounded worst case, which
        # is the right trade for user-facing search. The real fix is an index
        # that can filter and order at once -- a RUM index supports exactly
        # this (full-text match ordered by timestamp) and would beat both.
        return q1.order_by((Article.created + cast("0", Interval)).desc())
        #return q1.order_by(Article.created.desc())  # see above -- do not use


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


