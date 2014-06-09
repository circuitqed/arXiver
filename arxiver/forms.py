__author__ = 'dave'

from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField, BooleanField, SelectMultipleField, FieldList, SelectField, HiddenField, \
    widgets
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


class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class AuthorForm(Form):
    feeds = MultiCheckboxField(coerce=int)
    similar_authors = MultiCheckboxField(coerce=int)

    def author_id_articles(self, id):
        query = Author.author_id_articles(id).limit(5)
        return query

    def __init__(self, user=None, author=None, feed_id=None, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

        self.feeds.choices = [(f.id, f.name ) for f in user.feeds]
        if feed_id is not None:
            self.feeds.data = [feed_id]

        self.similar_authors.choices = [(a.id, str(a)) for a in author.similar_authors()]
        self.similar_authors.choices.insert(0, (author.id, str(author)))


class SearchForm(Form):
    title = TextField('title')
    author = TextField('author')
    keyword = TextField('keyword')
    category = SelectMultipleField()
    year = TextField('year')

    def __index__(self, *args, **kwargs):
        super.__init__(self, *args, **kwargs)
        self.category.choices = [(c.name, c.name) for c in Category.query.order_by('name')]


class SimpleSearchForm(Form):
    query = TextField('query')


# learned from https://gist.github.com/kageurufu/6813878
class FeedForm(Form):
    name = TextField('Name')
    public = BooleanField('Public')
    enable_email = BooleanField('Email subscribe')
    email_frequency = SelectField('Frequency', choices=( (0, 'Daily'), (1, 'Weekly'), (2, 'Monthly')), coerce=int)

    def populate_obj(self, obj):
        obj.public = self.public.data
        obj.name = self.name.data
        obj.timestamp = datetime.datetime.utcnow()

        return obj

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        if 'subscription' in kwargs:
            self.subscription = kwargs['subscription']
            # if self.subscription is not None:
            # self.enable_email.data = self.subscription.enable_email
            #     self.email_frequency.data = self.subscription.email_frequency
        else:
            self.subscription = None


class EditForm(Form):
    nickname = TextField('nickname', validators=[Required()])
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
        user = User.query.filter_by(nickname=self.nickname.data).first()
        if user != None:
            self.nickname.errors.append('This nickname is already in use. Please choose another one.')
            return False

        return True

