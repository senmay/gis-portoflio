from flask import Blueprint

geomapper_bp = Blueprint('geomapper', __name__, template_folder='templates')

from . import routes
