from flask import Flask, url_for, redirect, render_template,session, g
from flask import flash, request
import sqlite3
import re
import os
from passlib.apps import custom_app_context as pwd_context
from helpers import *

app = Flask(__name__)

# Load default config
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'QPA.db'),
    SECRET_KEY='development key',
))


#Send headers to browser - disabling caching for development
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    # rv.row_factory = sqlite3.Row
    return rv

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

#ATM unsure of necessity of index.html, remove?
@app.route('/')
@require_login
def index():
    db = get_db();
    if request.method == 'POST':
        if request.form['add']:
            return redirect(url_for('add_article'))
    else:
        query = ''' SELECT name,id from projects where 
                    user_id = :user_id LIMIT 50
                '''
        rows = db.execute(query, {'user_id' : session['id']})
    return render_template('dashboard.html', projects = rows)

@app.route('/register', methods=["GET", "POST"])
def register():
    session.clear()
    # logout user (clear session) TODO
    if request.method == 'POST':
        # connects to database
        db = get_db()
        #flag used to check if all entered data is valid
        register_form_valid = 1
        #checks that username is valid and not duplicate (a-z, A-Z, 0-9, _ - 1-15 letters)
        if (len(request.form.get('username')) < 1):
            register_form_valid = 0
            flash("No username entered")
        else:
            if not re.match("^[A-Za-z0-9_-]*$", request.form.get('username')):
                register_form_valid = 0
                flash("Username contains unallowed characters")
            if (len(request.form.get('username')) > 15):
                register_form_valid = 0
                flash("Username longer than 15 characters")
            if (db.execute("""SELECT EXISTS(SELECT 1 FROM users 
                            WHERE username=:username LIMIT 1);"""
                            , {'username' : request.form.get('username')})
                            .fetchone()[0]):
                register_form_valid = 0
                flash("Username already taken")

        #checks that password is valid
        if (not request.form.get('password')):
            register_form_valid = 0
            flash("No password entered")
        else:
            if (len(request.form.get('password')) < 5):
                register_form_valid = 0
                flash("Password is less than 5 characters")
            elif (len(request.form.get('password')) > 26):
                register_form_valid = 0
                flash("Password is more than 26 characters")
            if not re.match("^[A-Za-z0-9_-]*$", request.form.get('password')):
                register_form_valid = 0
                flash("Password contains unallowed characters")
        if (not request.form.get('passwordConfirmation')):
            register_form_valid = 0
            flash("No password confirmation entered")
        elif (request.form.get('password') != 
              request.form.get('passwordConfirmation')):
            register_form_valid = 0
            flash("Passwords do not match")

        
        if register_form_valid:
            #create hash for password
            hash = pwd_context.encrypt(request.form.get('password'))
            #inserts the dataset in the database
            query = ("""INSERT INTO users (username,hash) 
                     VALUES(:username,:hash)""")
            db.execute(query,{'username':request.form.get('username'),'hash':hash})
            db.commit()
            flash('Success!')
            return redirect(url_for('login'))
    #return to login page
    return render_template('register.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        #clears current user
        session.clear()
        username = request.form.get('username')
        password = request.form.get('password')
        #flag used to check if entered data is valid
        form_valid = 1
        #Checks that forms have been entered correctly
        if not username:
            form_valid = 0
            flash('Please enter username')
        if not password:
            form_valid = 0
            flash('Please enter password')

        if form_valid:
            db = get_db()
            #SQL query checking if user exists´with entered password
            query = 'SELECT id ,hash FROM users WHERE username=:username'
            row = db.execute(query, {'username':username}).fetchone()
            #Checks if username exists
            if not (row):
                flash('Invalid username/password')
            #If username does exist, verify the password against the saved hash
            elif pwd_context.verify(password,row[1]):
                #save userid in session
                session['id'] = row[0]
                flash('success!')
                return render_template('index.html')
            else:
                flash('Invalid username/password')

    return render_template('login.html')

@app.route('/logout')
def logout():
    #clears current user
    session.clear()
    #sends user to login page
    return redirect(url_for('login'))

@app.route('/articles', methods=["GET","POST"])
@require_login
def articles():
    db = get_db();
    if request.method == 'POST':
        if request.form['add']:
            return redirect(url_for('add_article'))
    else:
        query = ''' SELECT name,id from articles where 
                    user_id = :user_id LIMIT 50
                '''
        rows = db.execute(query, {'user_id' : session['id']})
    return render_template('articles.html', articles = rows)

@app.route('/article<article_id>', methods=["GET","POST"])
@require_login
def article(article_id):
    db = get_db()

    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        hours_per_unit = float(request.form.get('time'))
        unit = request.form.get('unit')

        if not name:
            flash("Please enter article name")

        else:
            db = get_db()
            if not price or price < 0:
                price = 0
            if not hours_per_unit or hours_per_unit < 0:
                hours_per_unit = 0
            if not unit:
                unit = ''

            query = '''UPDATE articles
                       SET name=:name, price=:price,hours_per_unit=:hours_per_unit, unit=:unit
                       WHERE user_id = :user_id AND id = :article_id
                    '''
            db.execute(query,{'user_id':session["id"],'name':name,'price':price,'hours_per_unit':hours_per_unit,'article_id': article_id, 'unit':unit})
            db.commit()
            return redirect(url_for('articles'))
        
    
    query = 'SELECT id, name, price, hours_per_unit, unit FROM articles WHERE (user_id = :user_id AND id = :article_id)'
    rows = db.execute(query,{'user_id' : session['id'],'article_id': article_id})        
    article = rows.fetchone()

    return render_template('article.html', article = article)

@app.route('/add_article', methods=["GET","POST"])
@require_login
def add_article():

    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        hours_per_unit = float(request.form.get('time'))
        unit = request.form.get('unit')

        if not name:
            flash("Please enter article name")

        else:
            db = get_db()
            if not price or price > 0:
                price = 0
            if not hours_per_unit or hours_per_unit > 0:
                hours_per_unit = 0
            query = '''INSERT INTO articles (user_id,name,price,hours_per_unit,unit) 
                       VALUES (:user_id,:name,:price,:hours_per_unit,:unit)
                    '''
            db.execute(query,{'user_id':session["id"],'name':name,'price':price,'hours_per_unit':hours_per_unit,'unit':unit})
            db.commit()
            return redirect(url_for('articles'))
    
    return render_template('add_article.html')