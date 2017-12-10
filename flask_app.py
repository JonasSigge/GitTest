from flask import Flask, url_for, redirect, render_template,session, g
from flask import flash, request
import sqlite3
import re
import os
from passlib.apps import custom_app_context as pwd_context
from helpers import *

app = Flask(__name__)


def log_and_execute(cursor, sql, *args):
    s = sql
    if len(args) > 0:
        # generates SELECT quote(?), quote(?), ...
        cursor.execute("SELECT " + ", ".join(["quote(?)" for i in args]), args)
        quoted_values = cursor.fetchone()
        for quoted_value in quoted_values:
            s = s.replace('?', str(quoted_value), 1)
    print ("SQL command: " + s)
    cursor.execute(sql, args)





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

#Index/dashboard showing projects
@app.route('/', methods=["GET"])
@require_login
def index():
    db = get_db();
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

@app.route('/articles/<project_id>', methods=["GET","POST"])
@require_login
def articles(project_id):
    db = get_db();
    if request.method == 'POST':
        if  request.form['add']:
            return redirect(url_for('add_article'))
    else:
        query = ''' SELECT name,id from articles where 
                    user_id = :user_id LIMIT 50
                '''
        rows = db.execute(query, {'user_id' : session['id']})
    return render_template('articles.html', articles = rows, project_id = project_id)

@app.route('/article/<project_id>/<article_id>', methods=["GET","POST"])
@require_login
def article(project_id,article_id):
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
            return redirect(url_for('articles', project_id = project_id))
        
    
    query = 'SELECT id, name, price, hours_per_unit, unit FROM articles WHERE (user_id = :user_id AND id = :article_id)'
    rows = db.execute(query,{'user_id' : session['id'],'article_id': article_id})        
    article = rows.fetchone()

    return render_template('article.html', article = article, project_id = project_id)

@app.route('/add_article/<project_id>', methods=["GET","POST"])
@require_login
def add_article(project_id):

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
            return redirect(url_for('articles',project_id = project_id))
    
    return render_template('add_article.html',project_id = project_id)

@app.route('/add_project', methods=["GET","POST"])
@require_login
def add_project():
    if request.method == 'POST':
        name = request.form.get('name')

        if not name:
            flash("Please enter project name")

        else:
            db = get_db()
            query = '''INSERT INTO projects (user_id,name) 
                       VALUES (:user_id,:name)
                    '''
            db.execute(query,{'user_id':session["id"],'name':name})
            db.commit()
            return redirect(url_for('index'))
    
    return render_template('add_project.html')

@app.route('/project<project_id>', methods=["GET","POST"])
@require_login
def project(project_id):
    db = get_db()

    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash("Please enter article name")
        else:
        #check if article is already in project
            query = '''

                    '''
            query = '''UPDATE Projects_articles
                       SET name=:name, price=:price,hours_per_unit=:hours_per_unit, unit=:unit
                       WHERE user_id = :user_id AND id = :article_id
                    '''
            db.execute(query,{'user_id':session["id"],'name':name,'price':price,'hours_per_unit':hours_per_unit,'article_id': article_id, 'unit':unit})
            db.commit()
            return redirect(url_for('index'))
        
    #Gets the articles and respective quantity related to this project
    query = 'SELECT article_id,quantity FROM Projects_articles WHERE (user_id = :user_id AND project_id = :project_id)'
    project_articles = db.execute(query,{'user_id' : session['id'],'project_id': project_id})
    #selected_articles = '","'.join([str(article[0]) for article in project_articles])

    selected_articles = [str(article[0]) for article in project_articles]
    #print(selected_articles)
    selected_articles = ','.join("'{0}'".format(x) for x in selected_articles)

    query = 'SELECT * FROM articles WHERE (user_id = :user_id) AND (id IN (:article_id))'
    articles = db.execute(query,{'user_id' : session['id'],'article_id': selected_articles})

    #query = 'SELECT * FROM articles WHERE (user_id = ?) AND (id IN (?))'
    #articles = db.execute(query,[session['id'],selected_articles])
    #log_and_execute(articles,query,session['id'],selected_articles)

    #print('SELECT * FROM articles WHERE (user_id = :user_id AND id IN (:article_id))')


    return render_template('project.html', articles = articles,project_id = project_id)

@app.route('/add_article_to_project/<project_id>/<article_id>', methods=["GET"])
@require_login
def add_article_to_project(project_id, article_id):

    db = get_db()

    #get project data
    query = 'SELECT * FROM projects WHERE id=:project_id AND user_id =:user_id'
    project = db.execute(query, {'project_id':project_id, 'user_id':session['id']}).fetchone()

    #get article data
    query = 'SELECT * FROM articles WHERE id=:article_id AND user_id =:user_id'
    article = db.execute(query, {'article_id':article_id, 'user_id':session['id']}).fetchone()

    #Checks that project and article info is OK
    if project and article:
        #check that article doesnt already exists in project
        query = 'SELECT id FROM Projects_articles WHERE article_id=:article_id AND project_id=:project_id AND user_id=:user_id'
        article_already_exists_in_project = db.execute(query,{'project_id':project_id,'article_id':article_id,'user_id':session['id']}).fetchone()

        if article_already_exists_in_project:
            flash('Article already exists')
            return(redirect(url_for('articles',project_id = project_id)))
        else:
            query = '''INSERT INTO Projects_articles (user_id,project_id,article_id,quantity) 
                       VALUES (:user_id,:project_id,:article_id,:quantity)
                    '''
            db.execute(query,{'user_id':session['id'],'project_id':project_id,'article_id':article_id,'quantity':int(1)})
            db.commit()
        return redirect(url_for('project',project_id = project_id))
    #insert new article into project

        #send user to project page
    return redirect(url_for('index'))



