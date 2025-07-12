import os
import rasterio
from werkzeug.utils import secure_filename
from flask import (render_template, request, flash, redirect, url_for, 
                   current_app)

from . import geouploader_bp
from .geoserver import publish_geotiff_directly

@geouploader_bp.route('/')
def index():
    """Renderuje stronę główną komponentu do wgrywania plików."""
    return render_template('geouploader.html')

@geouploader_bp.route('/upload', methods=['POST'])
def upload_file():
    """Obsługuje wgrywanie pliku i publikację w GeoServerze."""
    logger = current_app.logger
    config = current_app.config
    logger.info("Otrzymano nowe żądanie wgrania pliku przez komponent.")

    layer_name = request.form.get('layer_name')
    file = request.files.get('file')

    if not layer_name or not file or file.filename == '':
        flash("Błąd: Nazwa warstwy i plik są wymagane.", "danger")
        logger.warning("Formularz wysłany bez nazwy warstwy lub pliku.")
        return redirect(url_for('.index'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(config['UPLOAD_FOLDER'], filename)

    logger.info(f"Zapisywanie pliku '{filename}' do '{filepath}'")
    file.save(filepath)

    # Walidacja pliku GeoTIFF
    try:
        with rasterio.open(filepath) as dataset:
            if not dataset.crs:
                flash("Błąd: Plik nie zawiera informacji o układzie współrzędnych (CRS).", "danger")
                logger.error(f"Brak CRS w pliku: {filename}")
                return redirect(url_for('.index'))
            logger.info(f"Plik '{filename}' pomyślnie zwalidowany.")
    except rasterio.errors.RasterioIOError:
        flash("Błąd: Nieprawidłowy format pliku. Oczekiwano GeoTIFF.", "danger")
        logger.error(f"Błąd otwierania pliku jako GeoTIFF: {filename}.", exc_info=True)
        return redirect(url_for('.index'))

    # Publikacja w GeoServerze
    try:
        logger.info(f"Rozpoczynanie publikacji warstwy '{layer_name}'.")
        publish_geotiff_directly(layer_name, filepath)
        flash(f"Sukces! Warstwa '{layer_name}' została opublikowana w GeoServerze.", "success")
        logger.info(f"Pomyślnie opublikowano warstwę '{layer_name}'.")
    except Exception as e:
        flash(f"Błąd podczas publikacji w GeoServerze. Sprawdź logi.", "danger")
        logger.error(f"Błąd podczas publikacji warstwy '{layer_name}'.", exc_info=True)

    return redirect(url_for('.index'))
