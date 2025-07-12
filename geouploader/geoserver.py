import requests
from flask import current_app

def publish_geotiff_directly(layer_name, filepath):
    """
    Publikuje GeoTIFF przez bezpośrednie wysłanie pliku do GeoServera.
    Ta metoda tworzy CoverageStore i Layer w jednym kroku.
    """
    # Pobieranie konfiguracji i loggera z bieżącej aplikacji Flaska
    config = current_app.config
    logger = current_app.logger
    
    auth = (config['GEOSERVER_USER'], config['GEOSERVER_PASSWORD'])
    
    # Odczytanie zawartości pliku w trybie binarnym
    with open(filepath, 'rb') as f:
        file_data = f.read()

    # Ustawienie nagłówka dla danych binarnych GeoTIFF
    headers = {'Content-type': 'image/tiff'}
    
    # Budowanie URL-a do endpointu, który przyjmuje pliki
    url = (f"{config['GEOSERVER_URL']}/workspaces/{config['GEOSERVER_WORKSPACE']}"
           f"/coveragestores/{layer_name}/file.geotiff")
    
    logger.info(f"Wysyłanie żądania PUT z plikiem GeoTIFF do {url}")
    
    # Wysłanie żądania PUT z danymi pliku
    response = requests.put(url, data=file_data, auth=auth, headers=headers)

    # GeoServer powinien odpowiedzieć 201 (Created) lub 200 (OK), jeśli nadpisujemy
    if response.status_code not in [200, 201]:
        error_message = (f"Nie udało się opublikować pliku GeoTIFF. "
                         f"Status: {response.status_code}, Treść: {response.text}")
        logger.error(error_message)
        raise Exception(error_message)

    logger.info(f"Pomyślnie wysłano plik i opublikowano warstwę '{layer_name}'.")
