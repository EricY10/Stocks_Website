from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import time
from flask_socketio import SocketIO
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import random

# Initialize SQLAlchemy
db = SQLAlchemy()
migrate = Migrate()

# Initialize LoginManager
login_manager = LoginManager()

# Initialize SocketIO for real-time communication
socketio = SocketIO()

# Initialize APScheduler
scheduler = BackgroundScheduler()

def initialize_market_hours():
    from .models import MarketHours
    try:
        market_hours = MarketHours.query.first()  # Check if market hours already exist
        if not market_hours:
            # Set default opening and closing times
            default_open = time(9, 30)  # 9:30 AM
            default_close = time(16, 0)  # 4:00 PM
            
            # Create new MarketHours object and add to session
            market_hours = MarketHours(opening_time=default_open, closing_time=default_close)
            db.session.add(market_hours)
            db.session.commit()  # Commit to save the data to the database
            print("Default market hours initialized.")
        else:
            print("Market hours already exist.")
    except Exception as e:
        db.session.rollback()  # Rollback if any error occurs during commit
        print(f"An error occurred while initializing market hours: {e}")

def update_stock_prices():
    from .models import Stock
    with app.app_context():  # Ensure the Flask app context is active
        stocks = Stock.query.all()
        for stock in stocks:
            fluctuation = random.uniform(-0.05, 0.05)  # Change stock price by -5% to 5%
            old_price = stock.price
            stock.price += stock.price * fluctuation

            # Round the price to 2 decimal places
            stock.price = round(stock.price, 2)

            db.session.commit()  # Commit updated stock prices to the database
            
            # Emit price update to clients (pass the new price)
            socketio.emit('stock_price_update', {'new_price': stock.price})


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'your_secret_key'  
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/project_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  

    # Initialize the database
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize LoginManager
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User  # Import here to avoid circular import
        return User.query.get(int(user_id))

    # Initialize Flask-SocketIO
    socketio.init_app(app)

    # Initialize market hours
    with app.app_context():
        initialize_market_hours()

    # Set up a job to run every 10 seconds and update stock prices
    scheduler.add_job(func=update_stock_prices, trigger='interval', seconds=10)
    scheduler.start()

    # Register blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app

# Run the application with socketio.run() to handle both Flask and SocketIO events
app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True)
