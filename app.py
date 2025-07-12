import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template

from config import Config

def create_app(config_class=Config):
    """
    Fabryka aplikacji - tworzy i konfiguruje instancję aplikacji Flask.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

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

    # --- Rejestracja komponentu (Blueprintu) ---
    from geouploader import geouploader_bp
    # Komponent będzie dostępny pod adresem /geouploader
    app.register_blueprint(geouploader_bp, url_prefix='/geouploader')

    # --- Główna strona aplikacji (portfolio) ---
    @app.route('/')
    def home():
        """Renderuje główną stronę portfolio."""
        return render_template('home.html')

    return app
