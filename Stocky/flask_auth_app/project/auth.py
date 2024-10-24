from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Stock
from . import db

auth = Blueprint('auth', __name__)

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        admin = 'admin' in request.form  #  admin checkbox 

        new_user = User(email=email, name=name, password=generate_password_hash(password), admin=admin)
        
        db.session.add(new_user)
        db.session.commit()
     
        return redirect(url_for('auth.login'))

    return render_template('signup.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)

            if user.admin:
                return redirect(url_for('main.admin_page'))
            else:
                return redirect(url_for('main.index'))

    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


