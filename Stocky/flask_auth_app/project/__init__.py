from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate


# Initialize SQLAlchemy
db = SQLAlchemy()
migrate = Migrate()

# Initialize LoginManager
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

   
    app.config['SECRET_KEY'] = 'your_secret_key'  
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:Password!123@database-1.ct2gkce4mxle.us-east-1.rds.amazonaws.com/project_db'  
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
