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
    """Obsługuje wgrywanie pliku i publikację w GeoServerze."""
    logger = current_app.logger
    config = current_app.config
    logger.info("Otrzymano nowe żądanie wgrania pliku przez komponent.")

    layer_name = request.form.get('layer_name')
    epsg_code_str = request.form.get('epsg_code') # String from form
    original_filename_from_form = request.form.get('original_filename')

    file = request.files.get('file')

    # Determine the file to process: new upload or existing one
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(config['UPLOAD_FOLDER'], filename)
        logger.info(f"Zapisywanie nowego pliku '{filename}' do '{filepath}'")
        file.save(filepath)
    elif original_filename_from_form:
        filename = original_filename_from_form
        filepath = os.path.join(config['UPLOAD_FOLDER'], filename)
        logger.info(f"Używanie istniejącego pliku '{filename}' z '{filepath}'")
        if not os.path.exists(filepath):
            flash("Błąd: Oryginalny plik nie został znaleziony na serwerze. Proszę wgrać plik ponownie.", "danger")
            logger.error(f"Oryginalny plik '{filepath}' nie istnieje.")
            return redirect(url_for('.index'))
    else:
        flash("Błąd: Nazwa warstwy i plik są wymagane.", "danger")
        logger.warning("Formularz wysłany bez nazwy warstwy lub pliku.")
        return redirect(url_for('.index'))

    temp_output_filepath = None # This will hold the path to the file actually published

    try:
        with rasterio.open(filepath) as dataset:
            source_crs = dataset.crs
            source_bounds = dataset.bounds
            original_dataset_crs_is_none = (dataset.crs is None) # Flag to remember if original file had no CRS

            if not source_crs:
                # File has no CRS, try to use user-provided EPSG
                if not epsg_code_str:
                    # No CRS in file and no EPSG provided by user
                    flash("Błąd: Plik nie zawiera informacji o układzie współrzędnych (CRS). Proszę podać kod EPSG.", "warning")
                    logger.warning(f"Brak CRS w pliku '{filename}'. Prośba o EPSG.")
                    # Redirect with parameters to re-render the form with EPSG input
                    return redirect(url_for('.index', show_epsg_input=True, layer_name=layer_name, filename=filename))
                else:
                    # User provided EPSG, try to use it as source_crs
                    try:
                        epsg_code = int(epsg_code_str)
                        source_crs = rasterio.crs.CRS.from_epsg(epsg_code)
                        logger.info(f"Użyto EPSG {epsg_code} podanego przez użytkownika dla pliku '{filename}'.")
                    except ValueError:
                        flash("Błąd: Nieprawidłowy kod EPSG. Proszę podać prawidłowy numer.", "danger")
                        logger.error(f"Nieprawidłowy kod EPSG: {epsg_code_str}")
                        return redirect(url_for('.index', show_epsg_input=True, layer_name=layer_name, filename=filename))
                    except Exception as e:
                        flash(f"Błąd podczas przetwarzania kodu EPSG: {e}", "danger")
                        logger.error(f"Błąd CRS z EPSG {epsg_code_str}: {e}", exc_info=True)
                        return redirect(url_for('.index', show_epsg_input=True, layer_name=layer_name, filename=filename))
            
            # At this point, source_crs should be determined.
            if not source_crs: # Should not happen, but for safety
                flash("Błąd: Nie udało się określić układu współrzędnych dla pliku.", "danger")
                logger.error(f"Nie udało się określić CRS dla pliku '{filename}' po wszystkich próbach.")
                return redirect(url_for('.index'))

            logger.info(f"Plik '{filename}' pomyślnie zwalidowany. Oryginalny/Używany CRS: {source_crs}")

            # Check if the CRS is supported by GeoServer (geographic or projected)
            if not (source_crs.is_geographic or source_crs.is_projected):
                flash(f"Błąd: Układ współrzędnych {source_crs} nie jest obsługiwany przez GeoServer. GeoServer obsługuje tylko geograficzne i rzutowane systemy współrzędnych.", "danger")
                logger.error(f"Nieobsługiwany CRS {source_crs} dla pliku '{filename}'.")
                return redirect(url_for('.index', layer_name=layer_name, filename=filename))

            filepath_to_publish = filepath # Default to original file

            # If original file had no CRS but user provided a valid one, create a new GeoTIFF with embedded CRS
            # This is not reprojection, but writing the original data with the newly assigned CRS.
            if original_dataset_crs_is_none and epsg_code_str:
                fd, temp_output_filepath = tempfile.mkstemp(suffix='.tif')
                os.close(fd)

                with rasterio.open(filepath) as src_dataset:
                    profile = src_dataset.profile
                    profile.update({
                        'crs': source_crs, # Embed the user-provided CRS
                    })
                    with rasterio.open(temp_output_filepath, 'w', **profile) as dst:
                        # Copy data without reprojection, just update CRS
                        dst.write(src_dataset.read())
                filepath_to_publish = temp_output_filepath
                logger.info(f"Utworzono nowy GeoTIFF z CRS {source_crs} dla pliku '{filename}' (użytkownik podał EPSG).")

        # Publikacja w GeoServerze
        if not filepath_to_publish: # Should not happen if logic is correct
            flash("Błąd wewnętrzny: Nie udało się przygotować pliku do publikacji.", "danger")
            logger.error("filepath_to_publish is None before publishing.")
            return redirect(url_for('.index'))

        logger.info(f"Rozpoczynanie publikacji warstwy '{layer_name}' z pliku '{filepath_to_publish}'.")
        publish_geotiff_directly(layer_name, filepath_to_publish)
        flash(f"Sukces! Warstwa '{layer_name}' została opublikowana w GeoServerze.", "success")
        logger.info(f"Pomyślnie opublikowano warstwę '{layer_name}'.")

        # Convert source_bounds to EPSG:3857 for Leaflet map view
        logger.info(f"Original source_bounds: {source_bounds}")
        transformer = Transformer.from_crs(source_crs, "EPSG:3857", always_xy=True)
        minx_3857, miny_3857 = transformer.transform(source_bounds.left, source_bounds.bottom)
        maxx_3857, maxy_3857 = transformer.transform(source_bounds.right, source_bounds.top)
        bbox_epsg3857 = f"{minx_3857},{miny_3857},{maxx_3857},{maxy_3857}"
        logger.info(f"Converted bbox_epsg3857: {bbox_epsg3857}")

        redirect_url = url_for('wms_viewer', 
                                 layer_name=layer_name, 
                                 bbox_epsg3857=bbox_epsg3857)
        logger.info(f"Redirecting to: {redirect_url}")
        return redirect(redirect_url)

    except rasterio.errors.RasterioIOError:
        flash("Błąd: Nieprawidłowy format pliku. Oczekiwano GeoTIFF.", "danger")
        logger.error(f"Błąd otwierania pliku jako GeoTIFF: {filename}.", exc_info=True)
        return redirect(url_for('.index'))
    except Exception as e:
        flash(f"Błąd podczas publikacji w GeoServerze. Sprawdź logi.", "danger")
        logger.error(f"Błąd podczas publikacji warstwy '{layer_name}'.", exc_info=True)
    finally:
        # Clean up the temporary file if it was created and is different from the original
        if temp_output_filepath and temp_output_filepath != filepath and os.path.exists(temp_output_filepath):
            os.remove(temp_output_filepath)
            logger.info(f"Usunięto tymczasowy plik: {temp_output_filepath}")

    return redirect(url_for('.index'))