__author__ = 'dave'

import os
from flask import Flask, url_for, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.orderinglist import ordering_list
from flask_login import LoginManager
from flask_openid import OpenID
from config import basedir
from config import ARTICLES_PER_PAGE
from config import ADMINS, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD
# from flask.ext.restful import Api
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

# from social.apps.flask_app.routes import social_auth
# from social.apps.flask_app.models import init_social

from .flask_googlelogin import GoogleLogin
#from flask_oauth2_login import GoogleLogin

app = Flask(__name__, static_url_path='')
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#PSA login
#app.register_blueprint(social_auth)
#init_social(app,db)

lm = LoginManager()
lm.login_view = 'login2'
lm.init_app(app)
googlelogin = GoogleLogin(app,lm)
googlelogin.get_profile = lambda x: print ("get_profile")
#oid = OpenID(app,os.path.join(basedir,'tmp'))




#api = Api(app)



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
    # from logging.handlers import SMTPHandler
    # credentials = None
    # if MAIL_USERNAME or MAIL_PASSWORD:
    #     credentials = (MAIL_USERNAME,MAIL_PASSWORD)
    # mail_handler = SMTPHandler((MAIL_SERVER,MAIL_PORT),
    #     'no-reply@'+MAIL_SERVER,ADMINS,'microblog failure', credentials)
    # mail_handler.setLevel(logging.ERROR)
    # app.logger.addHandler(mail_handler)

    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler('tmp/' + __name__ + '.log', 'a', 1 * 1024 * 1024, 10)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.info(__name__ + ' startup')
from arxiver import models  #, apis
from arxiver.updater import Updater
from arxiver import views

#setup manager
manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('shell', Shell(make_context=lambda: {
    'app': app,
    'db': db
}))

manager.add_command('update', Updater())

