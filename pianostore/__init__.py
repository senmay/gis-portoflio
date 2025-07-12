# pianostore/__init__.py
from flask import Blueprint

pianostore_bp = Blueprint(
    'pianostore', 
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/pianostore/static' # Custom static path to avoid conflicts
)

# Import routes and models to make them available
from . import routes, models
