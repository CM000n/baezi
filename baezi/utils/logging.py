"""Logging-Setup für baezi."""

import logging


def setup_logging(log_level: str = "INFO", log_file: str = "baezi_import.log") -> None:
    """Konfiguriert Logging für die Anwendung.

    Args:
        log_level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Pfad zur Log-Datei
    """
    # Konvertiere String zu Log-Level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Root Logger konfigurieren
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )

    # requests Logger auf WARNING setzen (weniger verbose)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Erstellt Logger für ein Modul.

    Args:
        name: Name des Moduls (üblicherweise __name__)

    Returns:
        Logger-Instanz
    """
    return logging.getLogger(name)
