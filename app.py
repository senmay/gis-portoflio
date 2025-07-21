from flask import Flask, render_template, request, jsonify, current_app, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from geoalchemy2 import Geometry
import requests
import json
from datetime import datetime
import xml.etree.ElementTree as ET
from pyproj import Transformer
import re
import logging
from logging.handlers import RotatingFileHandler

from config import Config

db = SQLAlchemy()
mail = Mail()

class DrawnGeometry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    geom = db.Column(Geometry(geometry_type='GEOMETRY', srid=4326))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    mail.init_app(app)

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
    app.register_blueprint(geouploader_bp, url_prefix='/geouploader')
    
    # --- Główna strona aplikacji (portfolio) ---
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/projects')
    def projects():
        return render_template('projects.html')

    @app.route('/wms-viewer')
    def wms_viewer():
        return render_template('wms_viewer.html')

    @app.route('/api/layers')
    def get_wms_layers():
        try:
            config = current_app.config
            geoserver_rest_url = config['GEOSERVER_URL']
            geoserver_workspace = config['GEOSERVER_WORKSPACE']
            auth = (config['GEOSERVER_USER'], config['GEOSERVER_PASSWORD'])

            layers_url = f"{geoserver_rest_url}/workspaces/{geoserver_workspace}/layers.json"
            
            current_app.logger.info(f"Pobieranie listy warstw z: {layers_url}")
            
            response = requests.get(layers_url, auth=auth)
            response.raise_for_status()
            
            layers_data = response.json()
            layers = []
            
            if 'layers' in layers_data and 'layer' in layers_data['layers']:
                layer_list = layers_data['layers']['layer']
                if isinstance(layer_list, dict):
                    layer_list = [layer_list]
                    
                for layer_info in layer_list:
                    layers.append({
                        'name': layer_info['name'],
                        'title': layer_info.get('name', layer_info['name'])
                    })
            
            current_app.logger.info(f"Znaleziono {len(layers)} warstw")
            return jsonify({'layers': layers})
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Błąd połączenia z GeoServer: {e}", exc_info=True)
            return jsonify({'error': 'Błąd połączenia z GeoServer'}), 500
        except Exception as e:
            current_app.logger.error(f"Błąd podczas pobierania warstw: {e}", exc_info=True)
            return jsonify({'error': 'Błąd serwera podczas pobierania warstw'}), 500

    @app.route('/api/export-coordinates', methods=['POST'])
    def export_coordinates():
        try:
            data = request.get_json()
            if not data or 'coordinates' not in data:
                return jsonify({'error': 'Brak współrzędnych do eksportu'}), 400
            
            coordinates = data['coordinates']
            if not coordinates:
                return jsonify({'error': 'Lista współrzędnych jest pusta'}), 400
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            content = f"# Exported Coordinates - {timestamp}\n"
            content += "# Format: X, Y (EPSG:4326)\n"
            
            for coord in coordinates:
                if 'lng' in coord and 'lat' in coord:
                    content += f"{coord['lng']}, {coord['lat']}\n"
                elif 'x' in coord and 'y' in coord:
                    content += f"{coord['x']}, {coord['y']}\n"
            
            response = make_response(content)
            response.headers['Content-Type'] = 'text/plain'
            response.headers['Content-Disposition'] = f'attachment; filename=coordinates_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            
            current_app.logger.info(f"Eksportowano {len(coordinates)} współrzędnych")
            return response
            
        except Exception as e:
            current_app.logger.error(f"Błąd podczas eksportu współrzędnych: {e}", exc_info=True)
            return jsonify({'error': 'Błąd serwera podczas eksportu'}), 500

    @app.route('/api/layer-info/<layer_name>')
    def get_layer_info(layer_name):
        try:
            config = current_app.config
            auth = (config['GEOSERVER_USER'], config['GEOSERVER_PASSWORD'])
            
            url = f"{config['GEOSERVER_URL']}/workspaces/{config['GEOSERVER_WORKSPACE']}/layers/{layer_name}"
            
            current_app.logger.info(f"Pobieranie informacji o warstwie: {url}")
            
            response = requests.get(url, auth=auth, headers={'Accept': 'application/json'})
            
            if response.status_code == 404:
                return jsonify({'error': 'Warstwa nie została znaleziona'}), 404
            elif response.status_code != 200:
                current_app.logger.error(f"Błąd pobierania informacji o warstwie: {response.status_code} - {response.text}")
                return jsonify({'error': 'Nie można pobrać informacji o warstwie'}), 500
            
            layer_data = response.json()
            
            current_app.logger.info(f"Layer data structure: {layer_data}")
            
            layer_dict = layer_data.get('layer', {})
            
            layer_info = {
                'name': layer_dict.get('name', layer_name),
                'title': layer_dict.get('title', layer_name),
                'abstract': layer_dict.get('abstract', ''),
                'type': layer_dict.get('type', 'WMS'),
                'enabled': layer_dict.get('enabled', True),
                'wms_url': f"{config['GEOSERVER_URL'].replace('/rest', '')}/{config['GEOSERVER_WORKSPACE']}/wms"
            }
            
            if 'resource' in layer_dict:
                resource_url = layer_dict['resource']['href']
                resource_response = requests.get(resource_url, auth=auth, headers={'Accept': 'application/json'})
                
                if resource_response.status_code == 200:
                    resource_data = resource_response.json()
                    
                    bbox_info = None
                    source_crs = None
                    
                    if 'coverage' in resource_data:
                        coverage = resource_data['coverage']
                        if 'nativeBoundingBox' in coverage:
                            bbox_info = coverage['nativeBoundingBox']
                            source_crs = bbox_info.get('crs', 'EPSG:4326')
                    
                    elif 'featureType' in resource_data:
                        feature_type = resource_data['featureType']
                        if 'nativeBoundingBox' in feature_type:
                            bbox_info = feature_type['nativeBoundingBox']
                            source_crs = bbox_info.get('crs', 'EPSG:4326')
                    
                    if bbox_info:
                        try:
                            minx, miny = float(bbox_info['minx']), float(bbox_info['miny'])
                            maxx, maxy = float(bbox_info['maxx']), float(bbox_info['maxy'])
                            
                            layer_info['boundingBox'] = {
                                'minx': minx,
                                'miny': miny,
                                'maxx': maxx,
                                'maxy': maxy,
                                'crs': source_crs
                            }
                            
                            try:
                                if source_crs and source_crs != 'EPSG:3857':
                                    if 'EPSG' in str(source_crs):
                                        epsg_match = re.search(r'EPSG["\s]*[,:]?\s*["\s]*(\d+)', str(source_crs))
                                        if epsg_match:
                                            epsg_code = f"EPSG:{epsg_match.group(1)}"
                                            current_app.logger.info(f"Extracted EPSG code: {epsg_code}")
                                            transformer = Transformer.from_crs(epsg_code, "EPSG:3857", always_xy=True)
                                            minx_3857, miny_3857 = transformer.transform(minx, miny)
                                            maxx_3857, maxy_3857 = transformer.transform(maxx, maxy)
                                        else:
                                            current_app.logger.warning(f"Could not parse CRS {source_crs}, using original bounds")
                                            minx_3857, miny_3857 = minx, miny
                                            maxx_3857, maxy_3857 = maxx, maxy
                                else: # This means source_crs is 'EPSG:3857' or is not defined/parsed
                                    minx_3857, miny_3857 = minx, miny
                                    maxx_3857, maxy_3857 = maxx, maxy
                                    
                            except Exception as transform_error:
                                current_app.logger.warning(f"CRS transformation failed for {source_crs}: {transform_error}")
                                minx_3857, miny_3857 = minx, miny
                                maxx_3857, maxy_3857 = maxx, maxy
                            
                            if 'minx_3857' in locals():
                                layer_info['bbox_epsg3857'] = f"{minx_3857},{miny_3857},{maxx_3857},{maxy_3857}"
                            
                            current_app.logger.info(f"Layer {layer_name} bounds: {layer_info.get('bbox_epsg3857', 'not available')}")
                            
                        except Exception as e:
                            current_app.logger.error(f"Błąd calculating bounding box for layer {layer_name}: {e}")
            
            return jsonify(layer_info)
            
        except KeyError as e:
            current_app.logger.error(f"KeyError podczas pobierania informacji o warstwie: {e}", exc_info=True)
            return jsonify({'error': f'Brak wymaganego pola w odpowiedzi GeoServer: {e}'}), 500
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Błąd połączenia z GeoServer: {e}")
            return jsonify({'error': 'Błąd połączenia z GeoServer'}), 500
        except Exception as e:
            current_app.logger.error(f"Błąd podczas pobierania informacji o warstwie: {e}", exc_info=True)
            return jsonify({'error': 'Błąd serwera podczas pobierania informacji o warstwie'}), 500

    with app.app_context():
        db.create_all()

    return app
