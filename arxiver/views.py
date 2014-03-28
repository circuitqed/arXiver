__author__ = 'dave'

from datetime import datetime
from flask import render_template,redirect,flash, session, url_for, request,g
from flask.ext.login import login_user, logout_user, current_user,login_required
from arxiver import app #,db, lm, oid
#from forms import LoginForm,EditForm
#from models import User, ROLE_USER, ROLE_ADMIN

@app.route('/index')
@app.route('/')
def index():
    return "Hello world 2!"