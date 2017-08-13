
# A very simple Flask Hello World app for you to get started with...

from flask import Flask, url_for, redirect, render_template

app = Flask(__name__)

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/register')
def register():
	#TODO
	return redirect(url_for('index'))

@app.route('/login')
def login():
	#TODO
	return redirect(url_for('index'))

@app.route('/projectlist')
def projectlist():
	#TODO
	return redirect(url_for('index'))

@app.route('/articles')
def articles():
	#TODO
	return redirect(url_for('index'))
