from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import db
from project.models import User, Transaction, Stock

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    # Fetch current stock prices
    current_prices = Stock.query.all() 
    return render_template('index.html', current_prices=current_prices)

@main.route('/transactions') #/profile
@login_required
def transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    stocks_owned = {}

    for transaction in transactions:
        stock = Stock.query.get(transaction.stock_id)
        if stock:
            if stock.symbol in stocks_owned:
                stocks_owned[stock.symbol]['num_shares'] += transaction.num_shares if transaction.action == 'buy' else -transaction.num_shares
            else:
                stocks_owned[stock.symbol] = {
                    'stock_name': stock.name,
                    'symbol': stock.symbol,
                    'num_shares': transaction.num_shares if transaction.action == 'buy' else -transaction.num_shares,
                    'current_price': stock.price  # Include current price here
                }

    # Filter out stocks with 0 shares
    stocks_owned = {symbol: details for symbol, details in stocks_owned.items() if details['num_shares'] > 0}

    return render_template('transactions.html', transactions=transactions, stocks=stocks_owned)



@main.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_page():
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

    # Logic to retrieve current stocks and render the template
    current_prices = Stock.query.all()
    return render_template('admin.html', current_prices=current_prices)

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
    all_stocks = Stock.query.all()  # Fetch all stocks from the database
    return render_template('stocks.html', stocks=all_stocks)

@main.route('/stock/<int:stock_id>', methods=['GET', 'POST'])
@login_required
def stock_detail(stock_id):
    stock = Stock.query.get_or_404(stock_id)

    if request.method == 'POST':
        num_shares = int(request.form['num_shares'])
        action = request.form['action']  

        if action == 'buy':
            if num_shares > stock.available_shares:
                flash('Not enough shares available', 'danger')
            else:
                # Update stock available shares
                stock.available_shares -= num_shares
                
                # Create a new transaction
                transaction = Transaction(user_id=current_user.id, stock_id=stock.id,
                                          num_shares=num_shares, action='buy')
                db.session.add(transaction)
                db.session.commit()
                
                flash('Stock purchased successfully!', 'success')
                return redirect(url_for('main.transactions'))
        
        elif action == 'sell':
            # Check if the user owns enough shares to sell
            owned_shares = db.session.query(Transaction).filter_by(user_id=current_user.id, stock_id=stock.id, action='buy').with_entities(db.func.sum(Transaction.num_shares)).scalar() or 0
            
            if num_shares > owned_shares:
                flash('Not enough shares owned to sell', 'danger')
            else:
                # Update stock available shares
                stock.available_shares += num_shares
                
                # Create a new transaction for selling
                transaction = Transaction(user_id=current_user.id, stock_id=stock.id,
                                          num_shares=num_shares, action='sell')
                db.session.add(transaction)
                db.session.commit()
                
                flash('Stock sold successfully!', 'success')
                return redirect(url_for('main.transactions'))

    return render_template('stock_detail.html', stock=stock)
