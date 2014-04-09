__author__ = 'dave'

from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField, BooleanField, SelectMultipleField, FieldList
from wtforms.validators import Required, Length
from wtforms.ext.sqlalchemy.orm import model_form

from arxiver.models import User, Category, Feed
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


#learned from https://gist.github.com/kageurufu/6813878
class FeedForm(Form):
    name = TextField('Name')
    public = BooleanField('Public')
    authors = FieldList(TextField('Author'), min_entries=3)
    keywords = FieldList(TextField('Keyword'), min_entries=3)