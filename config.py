import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', "postgresql://arxiver:arxiver@db/arxiver")
SQLALCHEMY_TRACK_MODIFICATIONS = False

ARTICLES_PER_PAGE = 10

# administrator list
ADMINS = ['admin@lazybrains.com']

DEBUG_TB_INTERCEPT_REDIRECTS = False

GOOGLE_LOGIN_CLIENT_ID = os.environ.get('GOOGLE_LOGIN_CLIENT_ID', '')
GOOGLE_LOGIN_CLIENT_SECRET = os.environ.get('GOOGLE_LOGIN_CLIENT_SECRET', '')

UPDATE_TOKEN = os.environ.get('UPDATE_TOKEN', '')

GOOGLE_LOGIN_REDIRECT_SCHEME = "http"
GOOGLE_LOGIN_REDIRECT_PATH = "/oauth2callback"
