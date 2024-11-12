from flask import Blueprint, render_template, request, redirect, url_for, flash, redirect
from flask_login import login_required, current_user
from . import db
from .models import MarketHours
from project.models import User, Transaction, Stock, UserStock
from decimal import Decimal
from sqlalchemy import func
from functools import wraps
from datetime import time, datetime


main = Blueprint('main', __name__)

@main.app_context_processor
def inject_market_status():
    return dict(is_market_open=is_market_open())

@main.route('/')
@login_required
def index():
    market_hours = MarketHours.query.first()
    # Fetch current stock prices
    current_prices = Stock.query.all() 
    return render_template('index.html', current_prices=current_prices, market_hours=market_hours)

@main.route('/transactions') #/profile
@login_required
def transactions():
    market_hours = MarketHours.query.first()
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    stocks_owned = {}

    for transaction in transactions:
        stock = Stock.query.get(transaction.stock_id)
        if stock:
            if stock.symbol in stocks_owned:
                stocks_owned[stock.symbol]['num_shares'] += transaction.num_shares if transaction.action == 'buy' else -transaction.num_shares
            else:
                stocks_owned[stock.symbol] = {
                    'id': stock.id,
                    'stock_name': stock.name,
                    'symbol': stock.symbol,
                    'num_shares': transaction.num_shares if transaction.action == 'buy' else -transaction.num_shares,
                    'current_price': stock.price  
                }

    # Filter out stocks with 0 shares
    stocks_owned = {symbol: details for symbol, details in stocks_owned.items() if details['num_shares'] > 0}

    return render_template('transactions.html', transactions=transactions, stocks=stocks_owned, market_hours=market_hours)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.admin:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('main.index'))  
        return f(*args, **kwargs)
    return decorated_function

@main.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_page():
    market_hours = MarketHours.query.first()
    if not market_hours:
        default_open = time(9, 30)  # default 9:30 AM
        default_close = time(16, 0)  # default 4:00 PM
        market_hours = MarketHours(opening_time=default_open, closing_time=default_close)
        db.session.add(market_hours)
        db.session.commit()

    if request.method == 'POST':
        try:
            stock_name = request.form['stock_name']
            stock_symbol = request.form['stock_symbol']
            stock_price = request.form['stock_price']
            available_shares = request.form['available_shares']

            # Create a new Stock instance
            new_stock = Stock(symbol=stock_symbol, price=float(stock_price), available_shares=int(available_shares), name=stock_name)
            db.session.add(new_stock)
            db.session.commit()

            flash('Stock added successfully!', 'success')
            return redirect(url_for('main.admin_page'))
        except KeyError as e:
            flash(f'Missing field: {str(e)}', 'danger')
            return redirect(url_for('main.admin_page'))

    
    current_prices = Stock.query.all()
    users = User.query.all()  # Fetch all users from the database
    return render_template('admin.html', current_prices=current_prices, users=users, market_hours=market_hours)

@main.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required  
def delete_user(user_id):
    user_to_delete = User.query.get(user_id)  # Fetch the user by ID
    if user_to_delete:
        try:
            db.session.delete(user_to_delete)  
            db.session.commit()  
            flash('User deleted successfully!', 'success')  
        except Exception as e:
            db.session.rollback()  
            flash(f'Error deleting user: {str(e)}', 'danger')  
    else:
        flash('User not found!', 'danger')  
    return redirect(url_for('main.admin_page'))  

@main.route('/remove_stock/<int:stock_id>', methods=['POST'])
@login_required
def remove_stock(stock_id):
    if not current_user.admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.admin_page'))
    
    stock_to_remove = Stock.query.get_or_404(stock_id)

    try:
        db.session.delete(stock_to_remove)
        db.session.commit()
        flash('Stock removed successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing stock: {str(e)}', 'danger')

    return redirect(url_for('main.admin_page'))

@main.route('/stocks', methods=['GET'])
@login_required
def stocks():
    market_hours = MarketHours.query.first()
    all_stocks = Stock.query.all()  
    return render_template('stocks.html', stocks=all_stocks, market_hours=market_hours)

@main.route('/stock/<int:stock_id>', methods=['GET', 'POST'])
@login_required
def stock_detail(stock_id):
    stock = Stock.query.get_or_404(stock_id)

    # Get total bought shares and total sold shares for this user and stock
    bought_shares = (
        db.session.query(func.sum(Transaction.num_shares))
        .filter_by(user_id=current_user.id, stock_id=stock_id, action='buy')
        .scalar() or 0
    )
    sold_shares = (
        db.session.query(func.sum(Transaction.num_shares))
        .filter_by(user_id=current_user.id, stock_id=stock_id, action='sell')
        .scalar() or 0
    )
  
    owned_shares = bought_shares - sold_shares

    # Fetch the market hours
    market_hours = MarketHours.query.first()
    
   # Check if market_hours exists and compare current time with market hours
    if market_hours:
        current_time = datetime.now().time()
        if current_time < market_hours.opening_time or current_time > market_hours.closing_time:
            flash('The market is closed. You cannot buy or sell stocks outside of market hours.', 'danger')
            if request.method == 'POST':
                return redirect(url_for('main.stock_detail', stock_id=stock_id))  # Redirect on POST to avoid form submission
            else:
                return render_template('stock_detail.html', stock=stock, owned_shares=owned_shares)  # Render normally on GET


    if request.method == 'POST':
        num_shares = int(request.form['num_shares'])
        action = request.form['action']
        stock_price = Decimal(stock.price)

        if action == 'buy':
            if num_shares > stock.available_shares:
                flash('Not enough shares available', 'danger')
            else:
                # Update stock available shares
                stock.available_shares -= num_shares

                # Calculate total cost for the purchase
                total_cost = num_shares * stock_price

                # Check if the user has enough balance
                if current_user.balance >= total_cost:
                    # Deduct the total cost from user's balance
                    current_user.balance -= total_cost

                    # Create a new transaction for buying
                    transaction = Transaction(
                        user_id=current_user.id, stock_id=stock.id,
                        num_shares=num_shares, action='buy'
                    )
                    db.session.add(transaction)
                    db.session.commit()

                    flash('Stock purchased successfully!', 'success')
                    return redirect(url_for('main.stock_detail', stock_id=stock.id))
                else:
                    flash('Insufficient balance to complete the purchase', 'danger')

        elif action == 'sell':
            if num_shares > owned_shares:
                flash('You do not own enough shares to sell', 'danger')
            else:
                stock.available_shares += num_shares

                total_revenue = num_shares * stock_price

                current_user.balance += total_revenue

                transaction = Transaction(
                    user_id=current_user.id, stock_id=stock.id,
                    num_shares=num_shares, action='sell'
                )
                db.session.add(transaction)
                db.session.commit()

                flash(f'Successfully sold {num_shares} shares of {stock.name}', 'success')
                return redirect(url_for('main.stock_detail', stock_id=stock.id))

    return render_template('stock_detail.html', stock=stock, owned_shares=owned_shares)

@main.route('/sell/<stock_symbol>', methods=['GET', 'POST'])
@login_required
def sell_stock(stock_symbol):
    stock = Stock.query.filter_by(symbol=stock_symbol).first_or_404()

    market_hours = MarketHours.query.first()
    
    # Check if market_hours exists and compare current time with market hours
    if market_hours:
        current_time = datetime.now().time()
        if current_time < market_hours.opening_time or current_time > market_hours.closing_time:
            flash('The market is closed. You cannot sell stocks outside of market hours.', 'danger')
            return redirect(url_for('main.transactions'))

    if request.method == 'POST':
        num_shares_to_sell = int(request.form['num_shares'])
        stock_price = Decimal(stock.price)

        user_transactions = Transaction.query.filter_by(user_id=current_user.id, stock_id=stock.id).all()
        total_owned_shares = sum(
            [trans.num_shares if trans.action == 'buy' else -trans.num_shares for trans in user_transactions]
        )

        if num_shares_to_sell > total_owned_shares:
            flash('You do not own enough shares to sell', 'danger')
        else:
            stock.available_shares += num_shares_to_sell
 
            total_revenue = num_shares_to_sell * stock_price
            
            transaction = Transaction(user_id=current_user.id, stock_id=stock.id,
                                      num_shares=num_shares_to_sell, action='sell')
            db.session.add(transaction)
            current_user.balance += total_revenue
            db.session.commit()
            
            flash(f'Successfully sold {num_shares_to_sell} shares of {stock.name}', 'success')
            return redirect(url_for('main.transactions'))

    return redirect(url_for('main.transactions'))




@main.route('/update_balance', methods=['POST'])
@login_required
def update_balance():
    amount = Decimal(request.form.get('amount'))  
    transaction_type = request.form.get('transaction_type')

    if transaction_type == 'deposit':
        current_user.balance += amount
        flash(f'Successfully deposited ${amount:.2f}', 'success')
    elif transaction_type == 'withdrawal':
        if current_user.balance >= amount:
            current_user.balance -= amount
            flash(f'Successfully withdrew ${amount:.2f}', 'success')
        else:
            flash('Insufficient balance for this withdrawal', 'danger')

    db.session.commit()
    return redirect(url_for('main.transactions'))



# Market hours (24-hour format)
MARKET_OPEN = time(9, 30)   # 9:30 AM
MARKET_CLOSE = time(16, 0)  # 4:00 PM

def is_market_open():
    now = datetime.now().time()
    return MARKET_OPEN <= now <= MARKET_CLOSE




@main.route('/update_market_hours', methods=['POST'])
@login_required
@admin_required
def update_market_hours():
    new_opening_time = request.form.get('new_opening_time')
    new_closing_time = request.form.get('new_closing_time')
    
    market_hours = MarketHours.query.first()
    if market_hours:
        market_hours.opening_time = datetime.strptime(new_opening_time, '%H:%M').time()
        market_hours.closing_time = datetime.strptime(new_closing_time, '%H:%M').time()
        db.session.commit()
        
        flash("Market hours updated successfully!", 'success')
    else:
        flash("Market hours could not be updated.", 'danger')

    return redirect(url_for('main.admin_page'))
