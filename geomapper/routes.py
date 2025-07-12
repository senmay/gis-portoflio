from flask import render_template, request, jsonify, current_app
from shapely.geometry import shape
from geoalchemy2 import WKTElement

from . import geomapper_bp
from app import db, DrawnGeometry

@geomapper_bp.route('/', endpoint='index')
def draw():
    """Renderuje stronę do rysowania geometrii."""
    return render_template('geomapper.html')

@geomapper_bp.route('/api/save_geom', methods=['POST'])
def save_geom():
    data = request.get_json()
    if not data or 'geometry' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    try:
        # Konwersja GeoJSON na obiekt Shapely
        geometry = shape(data['geometry'])
        
        # Utworzenie WKTElement do zapisu w PostGIS
        wkt_element = WKTElement(geometry.wkt, srid=4326)
        
        new_geom = DrawnGeometry(geom=wkt_element)
        db.session.add(new_geom)
        db.session.commit()
        
        current_app.logger.info(f"Zapisano nową geometrię o ID: {new_geom.id}")
        return jsonify({'id': new_geom.id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Błąd podczas zapisu geometrii: {e}", exc_info=True)
        return jsonify({'error': 'Błąd serwera przy zapisie geometrii'}), 500
