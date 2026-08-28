import os
from flask import Flask, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import ARTICLES_PER_PAGE
from flask_migrate import Migrate

app = Flask(__name__, static_url_path='')
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

lm = LoginManager()
lm.login_view = 'login'
lm.init_app(app)
lm.login_message = 'Sign in to do that.'


def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


def datetimeformat(value, format='%H:%M / %d-%m-%Y'):
    return value.strftime(format)


app.jinja_env.filters['datetimeformat'] = datetimeformat
app.jinja_env.globals['url_for_other_page'] = url_for_other_page

if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler('tmp/' + __name__ + '.log', 'a', 1 * 1024 * 1024, 10)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.info(__name__ + ' startup')

from arxiver import models
from arxiver.updater import Updater
from arxiver import views
