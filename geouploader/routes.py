import os
import rasterio
from rasterio.warp import reproject, Resampling
from werkzeug.utils import secure_filename
from flask import (render_template, request, flash, redirect, url_for,
                   current_app)
import tempfile
import requests
from pyproj import Transformer

from . import geouploader_bp
from .geoserver import publish_geotiff_directly
from .validators import validate_file, validate_geotiff_and_get_bbox
from .exceptions.custom_exceptions import ValidationError

def get_geoserver_layers():
    config = current_app.config
    geoserver_rest_url = config['GEOSERVER_URL']
    geoserver_workspace = config['GEOSERVER_WORKSPACE']
    auth = (config['GEOSERVER_USER'], config['GEOSERVER_PASSWORD'])

    layers_url = f"{geoserver_rest_url}/workspaces/{geoserver_workspace}/layers.json"
    try:
        response = requests.get(layers_url, auth=auth)
        response.raise_for_status() # Raise an exception for HTTP errors
        layers_data = response.json()
        
        # Extract layer names
        layer_names = []
        if 'layers' in layers_data and 'layer' in layers_data['layers']:
            for layer_info in layers_data['layers']['layer']:
                # GeoServer REST API returns layer name as 'name' field
                layer_names.append(layer_info['name'])
        return layer_names
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas pobierania listy warstw z GeoServera: {e}", exc_info=True)
        return []

@geouploader_bp.route('/')
def index():
    """Renderuje stronę główną komponentu do wgrywania plików."""
    # Pass parameters to the template for re-rendering with EPSG input
    show_epsg_input = request.args.get('show_epsg_input', 'false').lower() == 'true'
    layer_name = request.args.get('layer_name', '')
    filename = request.args.get('filename', '')
    return render_template('geouploader.html', show_epsg_input=show_epsg_input, layer_name=layer_name, filename=filename)

@geouploader_bp.route('/view_wms')
def view_wms_layers():
    """Renderuje stronę do wyświetlania warstw WMS bez kontekstu uploadu."""
    return redirect(url_for('.display_wms'))

@geouploader_bp.route('/display_wms')
def display_wms():
    """Renderuje stronę do wyświetlania warstwy WMS."""
    layer_name = request.args.get('layer_name')
    bbox_epsg3857_str = request.args.get('bbox_epsg3857')
    
    config = current_app.config
    wms_workspace = config['GEOSERVER_WORKSPACE']
    wms_base_url = config['GEOSERVER_URL'].replace('/rest', '') + f"/{wms_workspace}/wms"

    available_layers = get_geoserver_layers()

    # Generic GetCapabilities URL for the template
    wms_capabilities_url = f"{config['GEOSERVER_URL'].replace('/rest', '')}/wms?service=WMS&version=1.3.0&request=GetCapabilities&namespace={wms_workspace}"

    return render_template('display_wms.html', 
                           layer_name=layer_name, 
                           wms_base_url=wms_base_url,
                           wms_workspace=wms_workspace,
                           available_layers=available_layers,
                           bbox_epsg3857=bbox_epsg3857_str,
                           wms_capabilities_url=wms_capabilities_url)

@geouploader_bp.route('/upload', methods=['POST'])
def upload_file():
    """Obsługuje wgrywanie pliku i publikację w GeoServerze lub chmurze COG."""
    logger = current_app.logger
    config = current_app.config
    logger.info("Otrzymano nowe żądanie wgrania pliku.")

    # Odczytanie danych z formularza
    layer_name = request.form.get('layer_name')
    publish_target = request.form.get('publish_target') # 'geoserver' or 'cog'
    epsg_code_str = request.form.get('epsg_code')
    original_filename_from_form = request.form.get('original_filename')
    file = request.files.get('file')

    try:
        filename, filepath = validate_file(file, config, original_filename_from_form)
    except ValidationError as e:
        flash(str(e), "danger")
        return redirect(url_for('.index'))

    try:
        source_crs, bbox_epsg3857 = validate_geotiff_and_get_bbox(filepath, epsg_code_str)

        # Publikacja w GeoServerze
        logger.info(f"Cel: GeoServer. Publikowanie warstwy '{layer_name}'.")
        publish_geotiff_directly(layer_name, filepath)
        flash(f"Sukces! Warstwa '{layer_name}' opublikowana w GeoServerze.", "success")
        return redirect(url_for('wms_viewer', layer_name=layer_name, bbox_epsg3857=bbox_epsg3857))

    except ValidationError as e:
        flash(str(e), "danger")
        return redirect(url_for('.index', show_epsg_input=True, layer_name=layer_name, filename=filename))
    except Exception as e:
        flash(f"Wystąpił nieoczekiwany błąd: {e}", "danger")
        logger.error(f"Błąd w upload_file dla warstwy '{layer_name}'.", exc_info=True)
        return redirect(url_for('.index'))

@geouploader_bp.route('/republish')
def republish_cog():
    """Tymczasowa trasa do testowania ponownej publikacji COG w GeoServerze."""
    logger = current_app.logger
    layer_name = request.args.get('layer_name')
    cog_url = request.args.get('cog_url')

    if not layer_name or not cog_url:
        return "Błąd: Wymagane parametry 'layer_name' i 'cog_url'.", 400

    try:
        logger.info(f"Rozpoczynanie ponownej publikacji warstwy '{layer_name}' z URL: {cog_url}")
        publish_cog_from_s3(layer_name, cog_url)
        flash(f"Sukces! Ponownie opublikowano warstwę '{layer_name}'.", "success")
        # Przekierowanie do ogólnego widoku, bo nie mamy BBOX
        return redirect(url_for('.display_wms', layer_name=layer_name))
    except Exception as e:
        logger.error(f"Błąd podczas ponownej publikacji warstwy '{layer_name}'.", exc_info=True)
        flash(f"Błąd podczas ponownej publikacji: {e}", "danger")
        return redirect(url_for('.index'))