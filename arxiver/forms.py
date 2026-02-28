from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectMultipleField, FieldList, SelectField, HiddenField, \
    widgets
from wtforms.validators import DataRequired, Length

from arxiver.models import *
from arxiver import db


class LoginForm(FlaskForm):
    openid = StringField('openid', validators=[DataRequired()])
    remember_me = BooleanField('remember_me', default=False)


class EditUserForm(FlaskForm):
    nickname = StringField('nickname', validators=[DataRequired()])
    fullname = StringField('fullname')
    about_me = TextAreaField('about_me', validators=[Length(min=0, max=140)])

    def __init__(self, original_nickname, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_nickname = original_nickname

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
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


class AuthorForm(FlaskForm):
    feeds = MultiCheckboxField(coerce=int)
    similar_authors = MultiCheckboxField(coerce=int)

    def author_id_articles(self, id):
        query = Author.author_id_articles(id).limit(5)
        return query

    def __init__(self, user=None, author=None, feed_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.feeds.choices = [(f.id, f.name ) for f in user.feeds]
        if feed_id is not None:
            self.feeds.data = [feed_id]

        self.similar_authors.choices = [(a.id,  a.__repr__()) for a in author.similar_authors()]
        self.similar_authors.choices.insert(0, (author.id, str(author)))


class SearchForm(FlaskForm):
    title = StringField('title')
    author = StringField('author')
    keyword = StringField('keyword')
    category = SelectMultipleField()
    year = StringField('year')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category.choices = [(c.name, c.name) for c in Category.query.order_by('name')]


class SimpleSearchForm(FlaskForm):
    query = StringField('query')


# learned from https://gist.github.com/kageurufu/6813878
class FeedForm(FlaskForm):
    name = StringField('Name')
    public = BooleanField('Public')
    enable_email = BooleanField('Email subscribe')
    email_frequency = SelectField('Frequency', choices=( (0, 'Daily'), (1, 'Weekly'), (2, 'Monthly')), coerce=int)

    def populate_obj(self, obj):
        obj.public = self.public.data
        obj.name = self.name.data
        obj.timestamp = datetime.datetime.utcnow()

        return obj

    def __init__(self, formdata=None, obj=None, subscription=None, **kwargs):
        super().__init__(formdata=formdata, obj=obj, **kwargs)
        self.subscription = subscription


class EditForm(FlaskForm):
    nickname = StringField('nickname', validators=[DataRequired()])
    fullname = StringField('fullname')
    email = StringField('email')
    enable_email = BooleanField('Email subscribe')
    email_frequency = SelectField('Frequency', choices=( ('0', 'Daily'), ('1', 'Weekly'), ('2', 'Monthly')))


    def __init__(self, original_nickname, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_nickname = original_nickname

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False
        if self.nickname.data == self.original_nickname:
            return True
        user = User.query.filter_by(nickname=self.nickname.data).first()
        if user != None:
            self.nickname.errors.append('This nickname is already in use. Please choose another one.')
            return False

        return True
