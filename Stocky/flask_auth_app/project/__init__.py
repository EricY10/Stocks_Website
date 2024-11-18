from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import SQLAlchemyError
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
        market_hours = MarketHours.query.first()
        if not market_hours:
            market_hours = MarketHours(opening_time=time(9, 30), closing_time=time(16, 0))
            db.session.add(market_hours)
            db.session.commit()
    except Exception:
        db.session.rollback()


def update_stock_prices():
    from .models import Stock
    with app.app_context():
        try:
            stocks = Stock.query.all()
            for stock in stocks:
                fluctuation = random.uniform(-0.05, 0.2)
                stock.price = round(stock.price * (1 + fluctuation), 2)
            db.session.commit()
            for stock in stocks:
                socketio.emit('stock_price_update', {'symbol': stock.symbol, 'new_price': stock.price})
        except SQLAlchemyError:
            db.session.rollback()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/project_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    socketio.init_app(app)

    with app.app_context():
        initialize_market_hours()

    scheduler.add_job(func=update_stock_prices, trigger='interval', seconds=1)
    scheduler.start()

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app


app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True)
