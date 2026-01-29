from flask import Flask
from config import Config
from app.models import db
from flask_migrate import Migrate

migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inicjalizacja rozszerzeń
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Rejestracja blueprintów
    from app.routes import auth, main, products, warehouse, orders, reports, customers
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(products.bp)
    app.register_blueprint(warehouse.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(customers.bp)
    
    # Tworzenie tabel w bazie danych
    with app.app_context():
        db.create_all()
    
    return app