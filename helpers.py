from flask import Flask,render_template,session,redirect,url_for
from functools import wraps

def require_login(f):

	@wraps(f)
	def wrapper(*args, **kwargs):
		if session.get("id") is None:
			return redirect(url_for('login'))

		return f(*args, **kwargs)

	return wrapper