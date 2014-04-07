__author__ = 'dave'

from flask import abort, request, make_response, url_for
from flask.ext.restful import Resource, reqparse, marshal, fields
from arxiver import api, db, app
from models import *
from sqlalchemy import or_, and_


class ArticleListAPI(Resource):
    def __init__(self):
        self.rparse = reqparse.RequestParser()
        self.rparse.add_argument('title', type=str, default="",
                                 required=False, help='Title Keyword')
        self.rparse.add_argument('author', type=str, default="",
                                 required=False, help='Author')
        self.rparse.add_argument('keyword', type=str, default="",
                                 required=False, help='Keyword all fields')
        self.rparse.add_argument('year', type=str, default="",
                                 required=False, help='Year')
        self.rparse.add_argument('category', type=str, default="",
                                 required=False, help='Category')
        super(ArticleListAPI, self).__init__()

    def get(self):
        args = self.rparse.parse_args()
        r = request
        print args
        author_fields = {
            'lastname': fields.String,
            'forenames': fields.String,
            'id': fields.Integer
        }

        article_fields = {
            'title': fields.String,
            'abstract': fields.String,
            'arxiv_id': fields.String,
            'id': fields.Integer,
            'created': fields.String,
            'updated': fields.String,
            'doi': fields.String,
            'journalref': fields.String,
            'authors': fields.List(fields.Nested(author_fields))
        }
        #print '%multi-resonator%'=='%'+title+'%'
        conditions = []
        if args['title'] != '':
            conditions.append(Article.title.ilike('%' + args['title'] + '%'))
        if args['keyword'] != '':
            conditions.append(or_(Article.title.ilike('%' + args['keyword'] + '%'),
                                  Article.abstract.ilike('%' + args['keyword'] + '%')))
        if args['author'] != '':
            conditions.append(Article.authors.any(Author.lastname.ilike(args['author'])))
        if conditions == []:
            return {}
        articles = Article.query.filter(and_(*conditions))
        print articles
        return map(lambda t: marshal(t, article_fields), articles)


class ArticleAPI(Resource):
    def get(self, id):
        a = Article.query.filter(Article.id == id).first()
        author_fields = {
            'lastname': fields.String,
            'forenames': fields.String,
            'id': fields.Integer
        }
        a = Article.query.filter(Article.id == id).first()
        article_fields = {
            'title': fields.String,
            'abstract': fields.String,
            'arxiv_id': fields.String,
            'id': fields.Integer,
            'created': fields.String,
            'updated': fields.String,
            'doi': fields.String,
            'journalref': fields.String,
            'comments': fields.String,
            'authors': fields.List(fields.Nested(author_fields))
        }
        if a is not None:
            return marshal(a, article_fields)
        else:
            return {}


class AuthorAPI(Resource):
    def get(self, id):
        a = Author.query.filter(Author.id == id).first()
        if a is None: return {}

        article_author_fields = {
            'lastname': fields.String,
            'forenames': fields.String,
            'id': fields.Integer
        }

        article_fields = {
            'title': fields.String,
            'abstract': fields.String,
            'arxiv_id': fields.String,
            'id': fields.Integer,
            'authors': fields.List(fields.Nested(article_author_fields))
        }

        author_fields = {
            'id': fields.Integer,
            'lastname': fields.String,
            'forenames': fields.String,
            'articles': fields.List(fields.Nested(article_fields))
        }
        ans = {}

        ans['author'] = marshal(a, author_fields)
        similar_authors = Author.query.filter(Author.lastname.ilike(a.lastname)).filter(
            Author.forenames.ilike(a.forenames[0] + '%'))
        if similar_authors is not None:
            ans['similar_authors'] = map(lambda t: marshal(t, article_author_fields), similar_authors)
        else:
            ans['similar_authors'] = []
        return ans


class FeedAPI(Resource):
    @staticmethod
    def marshal_feed(feed, include_articles=False):
        author_fields = {
            'lastname': fields.String,
            'forenames': fields.String,
            'id': fields.Integer
        }

        article_fields = {
            'title': fields.String,
            'abstract': fields.String,
            'authors': fields.List(fields.Nested(author_fields))
        }

        feed_fields = {
            'name': fields.String,
            'public': fields.Boolean,
            'creator': fields.Integer
        }
        ans = marshal(feed, feed_fields)
        if include_articles:
            ans['feed_articles'] = map(lambda t: marshal(t, article_fields), feed.feed_articles())
        return ans

    def get(self, id=None):
        print id
        f = Feed.query.filter(Feed.id == id).first()

        if f is None: return {}

        articles = f.feed_articles()

        author_fields = {
            'lastname': fields.String,
            'forenames': fields.String,
            'id': fields.Integer
        }

        article_fields = {
            'title': fields.String,
            'abstract': fields.String,
            'authors': fields.List(fields.Nested(author_fields))
        }
        return map(lambda t: marshal(t, article_fields), articles)

    def post(self):
        args = self.rparse.parse_args()
        f = Feed(name=args['name'], public=args['public'], creator=args['creator'],
                 timestamp=datetime.datetime.utcnow())
        for author_arg in args['authors']:
            a = Author.query.get(author_arg.id)
            f.authors.append(a)
        for keyword in args['keywords']:
            if id in keyword:
                kw = Keyword.query.get(keyword.id)
            else:
                kw = Keyword(keyword=keyword.keyword)
            f.keywords.append(kw)
        db.session.add(f)
        db.session.commit()

        return FeedAPI.marshal_feed(f)

    def put(self, id):
        args = self.rparse.parse_args()
        f = Feed(id=id, name=args['name'], public=args['public'], creator=args['creator'],
                 timestamp=datetime.datetime.utcnow())
        for author_arg in args['authors']:
            a = Author.query.get(author_arg.id)
            f.authors.append(a)
        for keyword in args['keywords']:
            if id in keyword:
                kw = Keyword.query.get(keyword.id)
            else:
                kw = Keyword(keyword=keyword.keyword)
            f.keywords.append(kw)
        db.session.add(f)
        db.session.commit()


class UserAPI(Resource):

    @staticmethod
    def marshal_user(user):
        author_fields = {
            'lastname': fields.String,
            'forenames': fields.String,
            'id': fields.Integer
        }

        keyword_fields={
            'id':fields.Integer,
            'keyword':fields.String
        }

        feed_fields = {
            'name': fields.String,
            'public': fields.Boolean,
            'creator': fields.Integer,
            'keywords': fields.List(fields.Nested(keyword_fields)),
            'authors': fields.List(fields.Nested(author_fields))
        }
        user_fields = {
            'id': fields.Integer,
            'fullname': fields.String,
            'email': fields.String,
            'feeds': fields.List(fields.Nested(feed_fields))
        }
        return marshal(user,user_fields)

    def get(self,id):
        user=User.query.get(id)
        return UserAPI.marshal_user(user)


api.add_resource(ArticleListAPI, '/api2/articles/', endpoint='articles')
api.add_resource(ArticleAPI, '/api2/articles/<int:id>', endpoint='article')
api.add_resource(AuthorAPI, '/api2/author/<int:id>', endpoint='author')
api.add_resource(FeedAPI, '/api2/feed/<int:id>', '/api2/feed/', endpoint='feed')
api.add_resource(UserAPI, '/api2/user/<int:id>','/api2/user/new', endpoint='user')