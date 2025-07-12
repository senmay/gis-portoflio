import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from geoalchemy2 import Geometry

from config import Config

db = SQLAlchemy()
mail = Mail()

class DrawnGeometry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    geom = db.Column(Geometry(geometry_type='GEOMETRY', srid=4326))

def create_app(config_class=Config):
    """
    Fabryka aplikacji - tworzy i konfiguruje instancję aplikacji Flask.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    mail.init_app(app)

    # Inicjalizacja dodatkowych elementów (np. folderu upload)
    config_class.init_app(app)

    # --- Konfiguracja logowania ---
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    log_file = 'app.log'
    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 5, backupCount=2)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    
    if not app.debug:
        app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('Aplikacja portfolio została uruchomiona')

    # --- Rejestracja komponentów (Blueprints) ---
    from geouploader import geouploader_bp
    from geomapper import geomapper_bp
    from pianostore import pianostore_bp
    from pianostore import email as pianostore_email
    
    app.register_blueprint(geouploader_bp, url_prefix='/geouploader')
    app.register_blueprint(geomapper_bp, url_prefix='/geomapper')
    app.register_blueprint(pianostore_bp, url_prefix='/piano-store')

    # Pass mail object to the email module
    pianostore_email.mail = mail

    # --- Główna strona aplikacji (portfolio) ---
    @app.route('/')
    def home():
        """Renderuje główną stronę portfolio."""
        return render_template('home.html')

    @app.route('/projects')
    def projects():
        """Renderuje stronę z projektami."""
        return render_template('projects.html')

    @app.route('/piano')
    def piano():
        """Renderuje stronę o mnie."""
        return render_template('piano.html')

    # Register CLI commands
    from pianostore import commands as pianostore_commands
    pianostore_commands.init_app(app)

    with app.app_context():
        db.create_all()

    return app
