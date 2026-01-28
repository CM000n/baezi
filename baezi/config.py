"""Konfigurationsmanagement für baezi."""

import os
from dataclasses import dataclass
from pathlib import Path

# Lade .env Datei falls vorhanden
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv nicht installiert


@dataclass
class Config:
    """Konfiguration für den Banking4 zu ezbookkeeping Import."""

    api_base_url: str
    api_token: str
    json_folder: Path
    min_booking_date: str
    log_level: str = "INFO"
    timezone: str = "Europe/Berlin"
    page_size: int = 50
    transfer_tolerance_days: int = 3

    @classmethod
    def from_env(cls) -> "Config":
        """Lädt Konfiguration aus Umgebungsvariablen.

        Returns:
            Config-Instanz mit Werten aus Umgebungsvariablen

        Raises:
            ValueError: Wenn erforderliche Umgebungsvariablen fehlen
        """
        api_token = os.getenv("BAEZI_API_TOKEN")
        if not api_token:
            raise ValueError(
                "BAEZI_API_TOKEN nicht gesetzt! "
                "Bitte setzen Sie die Umgebungsvariable oder erstellen Sie eine .env Datei."
            )

        json_folder_str = os.getenv("BAEZI_JSON_FOLDER", "/mnt/c/Users/simon/b4export")
        json_folder = Path(json_folder_str)

        return cls(
            api_base_url=os.getenv("BAEZI_API_URL", "http://192.168.176.3:8050/api/v1"),
            api_token=api_token,
            json_folder=json_folder,
            min_booking_date=os.getenv("BAEZI_MIN_DATE", "2024-01-15"),
            log_level=os.getenv("BAEZI_LOG_LEVEL", "INFO"),
            timezone=os.getenv("BAEZI_TIMEZONE", "Europe/Berlin"),
            page_size=int(os.getenv("BAEZI_PAGE_SIZE", "50")),
            transfer_tolerance_days=int(os.getenv("BAEZI_TRANSFER_TOLERANCE_DAYS", "3")),
        )

    @classmethod
    def from_args(
        cls,
        api_url: str | None = None,
        api_token: str | None = None,
        json_folder: str | None = None,
        min_date: str | None = None,
        log_level: str | None = None,
    ) -> "Config":
        """Erstellt Config aus CLI-Argumenten mit Fallback auf Umgebungsvariablen.

        Args:
            api_url: ezbookkeeping API URL
            api_token: API Token
            json_folder: Pfad zum Banking4 JSON Export Ordner
            min_date: Mindest-Buchungsdatum (YYYY-MM-DD)
            log_level: Log-Level (DEBUG, INFO, WARNING, ERROR)

        Returns:
            Config-Instanz
        """
        # Zuerst Config aus Env laden
        base_config = cls.from_env()

        # Dann CLI-Args überschreiben falls vorhanden
        if api_url:
            base_config.api_base_url = api_url
        if api_token:
            base_config.api_token = api_token
        if json_folder:
            base_config.json_folder = Path(json_folder)
        if min_date:
            base_config.min_booking_date = min_date
        if log_level:
            base_config.log_level = log_level

        return base_config

    def validate(self) -> None:
        """Validiert die Konfiguration.

        Raises:
            ValueError: Wenn Konfiguration ungültig ist
        """
        if not self.api_token:
            raise ValueError("API Token ist erforderlich")

        if not self.json_folder.exists():
            raise ValueError(f"JSON-Ordner nicht gefunden: {self.json_folder}")

        # Validiere Datumsformat
        from datetime import datetime

        try:
            datetime.strptime(self.min_booking_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Ungültiges Datumsformat für min_booking_date: {self.min_booking_date}. "
                f"Erwartet: YYYY-MM-DD"
            ) from e
