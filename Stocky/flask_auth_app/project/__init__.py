from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import time

# Initialize SQLAlchemy
db = SQLAlchemy()
migrate = Migrate()

# Initialize LoginManager
login_manager = LoginManager()

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

    with app.app_context():
        # Import models within app context to avoid circular imports
        from .models import User, UserStock
        # Create the database and tables
        db.create_all()

    # Register blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
