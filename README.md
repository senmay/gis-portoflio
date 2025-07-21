# Portfolio GIS & Web

Jest to projekt portfolio prezentujący umiejętności z zakresu GIS, programowania w Pythonie (Flask) oraz tworzenia aplikacji webowych.

## Struktura Projektu


- `geouploader`: Narzędzie do uploadu plików GeoTIFF i ich automatycznej publikacji jako warstwy WMS w GeoServerze.
- `pianostore`: Prosty sklep internetowy do sprzedaży nut (plików PDF) z symulacją procesu płatności.

---

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
    - Skopiuj plik `.env.example` do `.env` (jeśli istnieje) lub utwórz nowy plik `.env`.
    - Uzupełnij zmienne dla głównej aplikacji (PostgreSQL, GeoServer).
    - **Dodaj konfigurację dla wysyłki e-maili (wymagane dla sklepu):**
      ```
      # Ustawienia serwera SMTP (np. dla Gmaila)
      MAIL_SERVER=smtp.googlemail.com
      MAIL_PORT=587
      MAIL_USE_TLS=True
      MAIL_USERNAME=twoj-adres@gmail.com
      MAIL_PASSWORD=twoje-haslo-do-aplikacji # Ważne: użyj hasła aplikacji, nie hasła do konta!
      MAIL_DEFAULT_SENDER="Nazwa Sklepu <twoj-adres@gmail.com>"
      ```

5.  **Uruchom aplikację:**
    - Przed pierwszym uruchomieniem, utwórz bazę danych sklepu: `flask pianostore init-db`
    - Uruchom serwer: `flask run`

---

## Moduł Sklepu z Nutami (`pianostore`)

Moduł ten jest w pełni funkcjonalnym prototypem sklepu, który symuluje proces zakupu.

### Jak dodać nowe nuty?

1.  Umieść plik z okładką (np. `nowa-okladka.png`) w folderze `pianostore/static/img/`.
2.  Umieść plik PDF z nutami (np. `nowe-nuty.pdf`) w folderze `pianostore/static/pdf/`.
3.  Użyj poniższej komendy w terminalu, aby dodać produkt do bazy danych (aplikacja zapyta Cię o wszystkie szczegóły):
    ```bash
    flask pianostore add-product
    ```
4.  Po ponownym uruchomieniu aplikacji, nowy produkt pojawi się w sklepie.

### Jak działa "zakup"?

1.  Użytkownik klika "Kup Teraz" i podaje swój adres e-mail.
2.  Aplikacja symuluje pomyślną płatność, zapisuje zamówienie w lokalnej bazie danych SQLite (`pianostore.db`) i wysyła e-mail z unikalnym linkiem do pobrania.
3.  Kliknięcie w link pozwala pobrać plik PDF. Link jest powiązany z konkretnym zamówieniem.
