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


#SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'arxiver.db')
SQLALCHEMY_DATABASE_URI = "postgresql://arxiver:arxiver@localhost/arxiver"
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

ARTICLES_PER_PAGE = 10

# mail server settings
MAIL_SERVER = 'localhost'
MAIL_PORT = 8025
MAIL_USERNAME = None
MAIL_PASSWORD = None

# administrator list
ADMINS = ['admin@lazybrains.com']

# Twitter:
#
# app.config['SOCIAL_TWITTER'] = {
#     'consumer_key': 'twitter consumer key',
#     'consumer_secret': 'twitter consumer secret'
# }
# Facebook:
#
# app.config['SOCIAL_FACEBOOK'] = {
#     'consumer_key': 'facebook app id',
#     'consumer_secret': 'facebook app secret'
# }
# foursquare:
#
# app.config['SOCIAL_FOURSQUARE'] = {
#     'consumer_key': 'client id',
#     'consumer_secret': 'client secret'
# }
# Google:
#
# SOCIAL_GOOGLE = {
#     'consumer_key': '499231713930-piv0f3vrh9v9b5i6rvspa8oqd0hp83aq.apps.googleusercontent.com',
#     'consumer_secret': 'iacneFZ1bYEa6MPH12J3RquR'
# }

#required packages
#Flask
#Flask-SQLAlchemy
#Flask-social
#   -pip install http://github.com/pythonforfacebook/facebook-sdk/tarball/master
#   -pip install python-twitter
#   -pip install foursquare
#   -pip install oauth2client google-api-python-client


#python-social-auth
DEBUG_TB_INTERCEPT_REDIRECTS = False
#SESSION_PROTECTION = 'strong'
SESSION_COOKIE_NAME = 'psa_session'
SOCIAL_AUTH_LOGIN_URL = '/login2/'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_USER_MODEL = 'arxiver.models.User'
SOCIAL_AUTH_AUTHENTICATION_BACKENDS = (
    'social.backends.open_id.OpenIdAuth',
    'social.backends.google.GoogleOpenId',
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GoogleOAuth',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.yahoo.YahooOpenId',
    'social.backends.stripe.StripeOAuth2',
    'social.backends.persona.PersonaAuth',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.facebook.FacebookAppOAuth2',
    'social.backends.yahoo.YahooOAuth',
    'social.backends.angel.AngelOAuth2',
    'social.backends.behance.BehanceOAuth2',
    'social.backends.bitbucket.BitbucketOAuth',
    'social.backends.box.BoxOAuth2',
    'social.backends.linkedin.LinkedinOAuth',
    'social.backends.github.GithubOAuth2',
    'social.backends.foursquare.FoursquareOAuth2',
    'social.backends.instagram.InstagramOAuth2',
    'social.backends.live.LiveOAuth2',
    'social.backends.vk.VKOAuth2',
    'social.backends.dailymotion.DailymotionOAuth2',
    'social.backends.disqus.DisqusOAuth2',
    'social.backends.dropbox.DropboxOAuth',
    'social.backends.evernote.EvernoteSandboxOAuth',
    'social.backends.fitbit.FitbitOAuth',
    'social.backends.flickr.FlickrOAuth',
    'social.backends.livejournal.LiveJournalOpenId',
    'social.backends.soundcloud.SoundcloudOAuth2',
    'social.backends.thisismyjam.ThisIsMyJamOAuth1',
    'social.backends.stocktwits.StocktwitsOAuth2',
    'social.backends.tripit.TripItOAuth',
    'social.backends.clef.ClefOAuth2',
    'social.backends.twilio.TwilioAuth',
    'social.backends.xing.XingOAuth',
    'social.backends.yandex.YandexOAuth2',
    'social.backends.podio.PodioOAuth2',
    'social.backends.reddit.RedditOAuth2',
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '499231713930-piv0f3vrh9v9b5i6rvspa8oqd0hp83aq.apps.googleusercontent.com'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = 'iacneFZ1bYEa6MPH12J3RquR'

GOOGLE_LOGIN_CLIENT_ID='499231713930-piv0f3vrh9v9b5i6rvspa8oqd0hp83aq.apps.googleusercontent.com'
GOOGLE_LOGIN_CLIENT_SECRET='iacneFZ1bYEa6MPH12J3RquR'
#GOOGLE_LOGIN_REDIRECT_URI='http://localhost:5000/oauth2callback'

GOOGLE_LOGIN_REDIRECT_SCHEME = "http"
GOOGLE_LOGIN_REDIRECT_PATH = "/oauth2callback"
