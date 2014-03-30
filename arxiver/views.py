__author__ = 'dave'

from datetime import datetime
from flask import render_template, redirect, flash, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from arxiver import app  #,db, lm, oid
#from forms import LoginForm,EditForm
#from models import User, ROLE_USER, ROLE_ADMIN
from models import Category

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/test')
def test():
    print [c.name for c in Category.query.all()]
