from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Stock
from . import db

auth = Blueprint('auth', __name__)


def generate_password_hash_no_limit(password):
    return generate_password_hash(password)

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        admin = 'admin' in request.form  # admin checkbox

        # Check if the email is already registered
        if User.query.filter_by(email=email).first():
            flash('Email address already in use.', 'danger')
            return redirect(url_for('auth.signup'))

        # Hash the password without truncation
        hashed_password = generate_password_hash_no_limit(password)
        new_user = User(email=email, name=name, password=hashed_password, admin=admin)
        
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
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
            flash('Logged in successfully!', 'success')
            
            # Redirect based on admin status
            if user.admin:
                return redirect(url_for('main.admin_page'))
            else:
                return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
