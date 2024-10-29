from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Numeric
from datetime import datetime
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    admin = db.Column(db.Boolean, default=False)
    balance = db.Column(Numeric(10, 2), default=0.00)

    stocks = db.relationship('UserStock', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user_reference', lazy=True, cascade="all, delete-orphan")


class UserStock(db.Model):
    __tablename__ = 'user_stocks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_symbol = db.Column(db.String(10), nullable=False)
    num_shares = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<UserStock {self.stock_symbol} ({self.num_shares})>"

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    num_shares = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(10), nullable=False)  
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='user_transactions', lazy=True)  
    stock = db.relationship('Stock', backref='stock_transactions', lazy=True)  


class Stock(db.Model):
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    available_shares = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Stock {self.symbol}: {self.name}, Price: ${self.price}, Available: {self.available_shares}>'
