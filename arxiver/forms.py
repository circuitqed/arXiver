__author__ = 'dave'

from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField, BooleanField, SelectMultipleField, FieldList, SelectField
from wtforms.validators import Required, Length
from wtforms.ext.sqlalchemy.orm import model_form

from arxiver.models import *
from arxiver import db


class LoginForm(Form):
    openid = TextField('openid', validators=[Required()])
    remember_me = BooleanField('remember_me', default=False)


class EditUserForm(Form):
    nickname = TextField('nickname', validators=[Required()])
    fullname = TextField('fullname')
    about_me = TextAreaField('about_me', validators=[Length(min=0, max=140)])

    def __init__(self, original_nickname, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_nickname = original_nickname

    def validate(self):
        if not Form.validate(self):
            return False
        if self.nickname.data == self.original_nickname:
            return True
        user = User.query.filter_by(nickname=self.nickname.data).first()
        if user is not None:
            self.nickname.errors.append('This nickname is already in use. Please choose another one.')
            return False

        return True


class SearchForm(Form):
    title = TextField('title')
    author = TextField('author')
    keyword = TextField('keyword')
    category = SelectMultipleField(choices=[(c.name, c.name) for c in Category.query.order_by('name')])
    year = TextField('year')

class SimpleSearchForm(Form):
    query = TextField('query')

#learned from https://gist.github.com/kageurufu/6813878
class FeedForm(Form):
    name = TextField('Name')
    public = BooleanField('Public')
    enable_email = BooleanField('Email subscribe')
    email_frequency = SelectField('Frequency', choices=( ('0', 'Daily'), ('1', 'Weekly'), ('2', 'Monthly')))
    authors = FieldList(TextField('Author'), min_entries=1)
    keywords = FieldList(TextField('Keyword'), min_entries=1)

    def populate_obj(self, obj):
        authors = []
        for author_id in self.authors.data:
            try:
                aid=int(author_id)
                a = Author.query.filter(Author.id == aid).first()
            except:
                a=None
            if a is not None:
                authors.append(a)
        #print "authors: " , authors

        kws = []
        for k in self.keywords.data:
            kw = Keyword.query.filter(Keyword.keyword.ilike(k)).first()
            if kw is None:
                kw = Keyword(keyword=k)
                print kw.keyword
                db.session.add(kw)
                #db.session.commit()
            kws.append(kw)

        obj.public=self.public.data
        obj.name=self.name.data
        obj.timestamp=datetime.datetime.utcnow()
        obj.authors=authors
        obj.keywords=kws
        return obj


    def init_form(self,obj):
        self.name.data=obj.name
        self.public.data=obj.public
        self.enable_email.data=obj.enable_email
        self.email_frequency.data=obj.email_frequency
        for author in obj.authors:
            self.authors.append(str(author.id))
        for keyword in obj.keywords:
            self.keywords.append_entry(keyword.keyword)


class EditForm(Form):
    nickname = TextField('nickname', validators = [Required()])
    fullname = TextField('fullname')
    email = TextField('email')
    enable_email = BooleanField('Email subscribe')
    email_frequency = SelectField('Frequency', choices=( ('0', 'Daily'), ('1', 'Weekly'), ('2', 'Monthly')))



    def __init__(self, original_nickname, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_nickname = original_nickname

    def validate(self):
        if not Form.validate(self):
            return False
        if self.nickname.data == self.original_nickname:
            return True
        user = User.query.filter_by(nickname = self.nickname.data).first()
        if user != None:
            self.nickname.errors.append('This nickname is already in use. Please choose another one.')
            return False

        return True

