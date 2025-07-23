import os
from werkzeug.utils import secure_filename
from flask import current_app, flash
from .exceptions.custom_exceptions import ValidationError
import rasterio
from pyproj import Transformer

def validate_file(file, config, original_filename_from_form):
    """Waliduje plik wejściowy."""
    if file and file.filename != '':
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)

        if file_length > 100 * 1024 * 1024:  # 100 MB
            raise ValidationError("Błąd: Plik jest za duży. Maksymalny rozmiar to 100 MB.")

        filename = secure_filename(file.filename)
        filepath = os.path.join(config['UPLOAD_FOLDER'], filename)
        current_app.logger.info(f"Zapisywanie nowego pliku '{filename}' do '{filepath}'")
        file.save(filepath)
        return filename, filepath

    elif original_filename_from_form:
        filename = original_filename_from_form
        filepath = os.path.join(config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            raise ValidationError("Błąd: Oryginalny plik nie został znaleziony.")
        return filename, filepath

    else:
        raise ValidationError("Błąd: Nazwa warstwy i plik są wymagane.")

def validate_geotiff_and_get_bbox(filepath, epsg_code_str):
    """Waliduje plik GeoTIFF, jego CRS i zwraca BBOX w EPSG:3857."""
    try:
        with rasterio.open(filepath) as dataset:
            source_crs = dataset.crs
            source_bounds = dataset.bounds

            if not source_crs and not epsg_code_str:
                raise ValidationError("Plik nie ma zdefiniowanego CRS. Proszę podać kod EPSG.")

            if epsg_code_str:
                try:
                    source_crs = rasterio.crs.CRS.from_epsg(int(epsg_code_str))
                except ValueError:
                    raise ValidationError("Nieprawidłowy kod EPSG.")

            if not source_crs:
                raise ValidationError("Nie udało się określić CRS.")

            transformer = Transformer.from_crs(source_crs, "EPSG:3857", always_xy=True)
            minx_3857, miny_3857 = transformer.transform(source_bounds.left, source_bounds.bottom)
            maxx_3857, maxy_3857 = transformer.transform(source_bounds.right, source_bounds.top)
            bbox_epsg3857 = f"{minx_3857},{miny_3857},{maxx_3857},{maxy_3857}"

            return source_crs, bbox_epsg3857
    except rasterio.errors.RasterioIOError:
        raise ValidationError("Nieprawidłowy format pliku. Oczekiwano GeoTIFF.")
