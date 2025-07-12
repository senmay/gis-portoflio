import os

class Config:
    """Przechowuje konfigurację aplikacji."""
    
    # Klucz do obsługi sesji i wiadomości flash
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super_secret_key_for_flash_messages')
    
    # Konfiguracja GeoServera
    GEOSERVER_URL = os.environ.get('GEOSERVER_URL', "http://localhost:8080/geoserver/rest")
    GEOSERVER_WORKSPACE = os.environ.get('GEOSERVER_WORKSPACE', "host_strona")
    GEOSERVER_USER = os.environ.get("GEOSERVER_USER", "admin")
    GEOSERVER_PASSWORD = os.environ.get("GEOSERVER_PASSWORD", "geoserver")
    
    # Konfiguracja ścieżek
    # Używamy os.path.abspath, aby zapewnić, że ścieżka jest zawsze poprawna
    UPLOAD_FOLDER = os.path.abspath('orto_ref_host')

    # Upewnij się, że katalog do uploadu istnieje
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

