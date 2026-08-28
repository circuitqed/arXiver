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

UPDATE_TOKEN = os.environ.get('UPDATE_TOKEN', '')

# --- Magic-link sign-in -------------------------------------------------
# Public origin, used to build the link that goes in the email. Must be
# the address the user actually browses to, not the container's.
APP_URL = os.environ.get('APP_URL', 'http://localhost:7854')

# 'console' writes the mail to the app log (dev); 'resend' delivers it.
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'console')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'arXiver <arxiver@send.lazybrains.com>')

# Optional gate on who may sign in. Comma-separated; entries are either a
# full address (dave@example.com) or a bare domain (stanford.edu) which
# matches anything at it. Empty means anyone with a working mailbox --
# which is what Google sign-in allowed before.
SIGNIN_ALLOWLIST = os.environ.get('SIGNIN_ALLOWLIST', '')

# The session cookie carries the login. Sessions last a browser session
# unless "remember me" is ticked, in which case the remember cookie runs
# for 90 days.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.environ.get('COOKIE_SECURE', '1') == '1'
REMEMBER_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_SAMESITE = 'Lax'
REMEMBER_COOKIE_SECURE = os.environ.get('COOKIE_SECURE', '1') == '1'
REMEMBER_COOKIE_DURATION = 90 * 24 * 60 * 60
