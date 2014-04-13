import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True 
SECRET_KEY = 'this is a secret key'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]


SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'arxiver.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

ARTICLES_PER_PAGE = 10

# mail server settings
MAIL_SERVER = 'localhost'
MAIL_PORT = 8025
MAIL_USERNAME = None
MAIL_PASSWORD = None

# administrator list
ADMINS = ['admin@lazybrains.com']
