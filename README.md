# Portfolio GIS & Web

To jest projekt portfolio prezentujący umiejętności z zakresu GIS, programowania w Pythonie (Flask) oraz tworzenia aplikacji webowych. Główne komponenty to narzędzie do przesyłania plików GeoTIFF z funkcją publikacji WMS oraz przeglądarka WMS.

## Jak to działa?

Aplikacja oferuje dwa odrębne przepływy pracy do publikowania danych geoprzestrzennych:

1.  **Bezpośrednio do GeoServera:**
    *   Użytkownik przesyła plik GeoTIFF bezpośrednio przez interfejs webowy.
    *   Backend, zbudowany przy użyciu Flaska, odbiera plik.
    *   Plik jest następnie przesyłany do instancji GeoServera za pomocą GeoServer REST API, udostępniając go jako warstwę WMS.

2.  **Cloud-Optimized GeoTIFF (COG) na AWS S3:**
    *   Użytkownik przesyła plik GeoTIFF.
    *   Backend konwertuje plik GeoTIFF na format Cloud-Optimized GeoTIFF (COG).
    *   Plik COG jest przesyłany do bucketa Amazon S3.
    *   W GeoServerze tworzona jest warstwa WMS, która odwołuje się do pliku COG na S3. To podejście jest bardziej skalowalne i wydajne dla dużych zbiorów danych.

## Struktura Projektu

*   `geouploader`: Główny moduł do obsługi przesyłania plików, przetwarzania GeoTIFF i publikowania w GeoServerze.
*   `wms-viewer`: Przeglądarka internetowa dla warstw WMS z GeoServera, z funkcjami takimi jak eksport współrzędnych i pomiary.
*   `static`: Zawiera statyczne zasoby, takie jak CSS i JavaScript.
*   `templates`: Zawiera szablony HTML aplikacji.

## Instalacja i Uruchomienie

1.  **Sklonuj repozytorium:**
    ```bash
    git clone <adres-repozytorium>
    cd <nazwa-folderu>
    ```

2.  **Utwórz i aktywuj środowisko wirtualne:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Zainstaluj zależności:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Skonfiguruj zmienne środowiskowe:**
    *   Utwórz plik `.env`.
    *   Uzupełnij niezbędne zmienne dla aplikacji (np. dane dostępowe do PostgreSQL, GeoServera).

5.  **Uruchom aplikację:**
    ```bash
    flask run
    ```
