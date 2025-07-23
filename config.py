import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Przechowuje konfigurację aplikacji."""
    
    # Klucz do obsługi sesji i wiadomości flash
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super_secret_key_for_flash_messages') 
    

    # Konfiguracja dla wysyłki e-maili
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Konfiguracja GeoServera
    GEOSERVER_URL = os.environ.get('GEOSERVER_URL', "http://localhost:8080/geoserver/rest")
    GEOSERVER_WORKSPACE = os.environ.get('GEOSERVER_WORKSPACE', "host_strona")
    GEOSERVER_USER = os.environ.get("GEOSERVER_USER", "admin")
    GEOSERVER_PASSWORD = os.environ.get("GEOSERVER_PASSWORD", "geoserver")

    # Konfiguracja bazy danych PostGIS
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:password@localhost:5432/gisdb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Konfiguracja ścieżek
    # Używamy os.path.abspath, aby zapewnić, że ścieżka jest zawsze poprawna
    UPLOAD_FOLDER = os.path.abspath('orto_ref_host')

    # Upewnij się, że katalog do uploadu istnieje
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Konfiguracja AWS S3 dla COG
    S3_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
    S3_SECRET = os.environ.get('AWS_SECRET_ACCESS_KEY')
    S3_BUCKET = os.environ.get('AWS_BUCKET_NAME')
    S3_LOCATION = os.environ.get('AWS_REGION')
    AWS_FOLDER = os.environ.get('AWS_FOLDER_NAME')
    AWS_ENDPOINT = os.environ.get('AWS_ENDPOINT')

