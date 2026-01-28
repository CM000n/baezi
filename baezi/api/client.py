"""API-Client für ezbookkeeping."""

import logging
import time as time_lib
from typing import Any

import requests

from baezi.config import Config

logger = logging.getLogger(__name__)


class APIError(Exception):
    """API-spezifische Fehler."""

    def __init__(self, status_code: int, message: str, response: str | None = None):
        self.status_code = status_code
        self.response = response
        super().__init__(f"API Error {status_code}: {message}")


class EzbookkeepingClient:
    """Client für ezbookkeeping API.

    Bietet zentralisierte API-Kommunikation mit Error-Handling,
    automatischer Header-Verwaltung und Retry-Logik.
    """

    def __init__(self, config: Config):
        """Initialisiert den API-Client.

        Args:
            config: Konfiguration mit API-URL und Token
        """
        self.config = config
        self.base_url = config.api_base_url
        self.session = requests.Session()
        self.session.headers.update(self._get_headers())

    def _get_utc_offset_minutes(self) -> int:
        """Berechnet UTC-Offset in Minuten."""
        if time_lib.localtime().tm_isdst and time_lib.daylight:
            return -int(time_lib.altzone / 60)
        return -int(time_lib.timezone / 60)

    def _get_headers(self) -> dict[str, str]:
        """Erstellt HTTP-Headers für API-Requests.

        Returns:
            Dictionary mit HTTP-Headers
        """
        return {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json",
            "X-Timezone-Name": self.config.timezone,
            "X-Timezone-Offset": str(self._get_utc_offset_minutes()),
        }

    def _request(
        self, method: str, endpoint: str, raise_on_error: bool = True, **kwargs: Any
    ) -> dict[str, Any]:
        """Führt API-Request aus mit Error-Handling.

        Args:
            method: HTTP-Methode (GET, POST, etc.)
            endpoint: API-Endpoint (relativ zur base_url)
            raise_on_error: Ob bei Fehler Exception geworfen werden soll
            **kwargs: Zusätzliche Argumente für requests

        Returns:
            JSON-Response als Dictionary

        Raises:
            APIError: Bei API-Fehlern (wenn raise_on_error=True)
        """
        url = f"{self.base_url}/{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)

            if raise_on_error:
                response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP-Fehler bei {method} {endpoint}"
            logger.error(f"{error_msg}: {e}")
            raise APIError(
                response.status_code, error_msg, response.text[:200] if response else None
            ) from e

        except requests.exceptions.RequestException as e:
            error_msg = f"Request-Fehler bei {method} {endpoint}"
            logger.error(f"{error_msg}: {e}")
            raise APIError(0, error_msg) from e

        except ValueError as e:
            # JSON decode error
            error_msg = "Ungültige JSON-Response"
            logger.error(f"{error_msg}: {e}")
            raise APIError(0, error_msg) from e

    # ==================== Transactions ====================

    def get_transactions(self, page: int = 1, page_size: int | None = None) -> dict[str, Any]:
        """Lädt Transaktionen (paginiert).

        Args:
            page: Seitennummer (1-basiert)
            page_size: Anzahl Transaktionen pro Seite

        Returns:
            API-Response mit Transaktionen
        """
        if page_size is None:
            page_size = self.config.page_size

        return self._request("GET", f"transactions/list.json?page={page}&count={page_size}")

    def get_all_transactions(self) -> list[dict[str, Any]]:
        """Lädt ALLE Transaktionen über Paging.

        Returns:
            Liste aller Transaktionen
        """
        all_transactions = []
        page = 1

        while True:
            resp = self.get_transactions(page=page)

            if not resp.get("success") or not resp["result"]["items"]:
                break

            all_transactions.extend(resp["result"]["items"])

            # Prüfen ob letzte Seite erreicht
            if len(resp["result"]["items"]) < self.config.page_size:
                break

            page += 1

        logger.debug(f"Insgesamt {len(all_transactions)} Transaktionen geladen")
        return all_transactions

    def create_transaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Erstellt neue Transaktion.

        Args:
            payload: Transaktionsdaten

        Returns:
            API-Response

        Raises:
            APIError: Bei Fehler
        """
        return self._request("POST", "transactions/add.json", json=payload)

    # ==================== Categories ====================

    def get_categories(self) -> dict[str, Any]:
        """Lädt alle Kategorien.

        Returns:
            API-Response mit Kategorien
        """
        return self._request("GET", "transaction/categories/list.json")

    def create_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Erstellt neue Kategorie.

        Args:
            payload: Kategorie-Daten

        Returns:
            API-Response

        Raises:
            APIError: Bei Fehler
        """
        return self._request("POST", "transaction/categories/add.json", json=payload)

    # ==================== Accounts ====================

    def get_accounts(self) -> dict[str, Any]:
        """Lädt alle Accounts.

        Returns:
            API-Response mit Accounts
        """
        return self._request("GET", "accounts/list.json")

    # ==================== Health Check ====================

    def health_check(self) -> bool:
        """Prüft ob API erreichbar ist.

        Returns:
            True wenn API erreichbar, sonst False
        """
        try:
            resp = self._request("GET", "accounts/list.json", raise_on_error=False)
            return resp.get("success", False)
        except Exception as e:
            logger.error(f"Health-Check fehlgeschlagen: {e}")
            return False
