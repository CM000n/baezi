# 🏦 baezi

**Banking4 zu ezbookkeeping Importer**

Ein Python-Tool zum automatischen Import von Banking4-Transaktionen in [ezbookkeeping](https://github.com/mayswind/ezbookkeeping).

## ✨ Features

- ✅ **Automatischer Import** von Banking4 JSON-Exports
- ✅ **Transfer-Matching**: Automatische Erkennung zusammengehöriger Umbuchungen
- ✅ **Kategorien-Mapping**: Banking4-Kategorien werden automatisch in ezbookkeeping übernommen
- ✅ **Duplikat-Erkennung**: Bereits importierte Transaktionen werden übersprungen
- ✅ **Account-Mapping**: Flexible Zuordnung über Banking4-IDs im Kommentarfeld
- ✅ **Datumsfilter**: Import nur ab bestimmtem Buchungsdatum
- ✅ **Externe Transfers**: Korrekte Behandlung von Transfers zu nicht existierenden Konten

## 📋 Anforderungen

- Python 3.12+
- Poetry (für Dependency-Management)
- Zugriff auf eine ezbookkeeping-Instanz
- Banking4 JSON-Exports

## 🚀 Installation

### 1. Repository klonen

```bash
git clone https://github.com/CM000n/baezi.git
cd baezi
```

### 2. Dependencies installieren

```bash
poetry install
```

### 3. Konfiguration erstellen

Kopieren Sie die Beispiel-Konfiguration:

```bash
cp .env.example .env
```

Bearbeiten Sie `.env` und tragen Sie Ihre Daten ein:

```env
BAEZI_API_URL=http://192.168.176.3:8050/api/v1
BAEZI_API_TOKEN=your-api-token-here
BAEZI_JSON_FOLDER=/path/to/banking4/exports
BAEZI_MIN_DATE=2024-01-15
```

**⚠️ Wichtig:** Die `.env` Datei ist in `.gitignore` eingetragen und wird NICHT ins Repository committed!

## 📖 Verwendung

### CLI-Modus

```bash
# Mit .env Konfiguration
poetry run baezi

# Mit CLI-Optionen (überschreiben .env)
poetry run baezi --json-folder /path/to/exports --min-date 2024-01-01

# Debug-Ausgaben
poetry run baezi --verbose

# Hilfe anzeigen
poetry run baezi --help
```

### Als Python-Modul

```bash
python -m baezi
```

### Programmatische Verwendung

```python
from baezi import Config, EzbookkeepingClient
from baezi.services import AccountService, CategoryService, TransactionImportService

# Config laden
config = Config.from_env()

# Services initialisieren
api_client = EzbookkeepingClient(config)
account_service = AccountService(api_client)
category_service = CategoryService(api_client)

# Daten laden
account_service.load_account_map()
category_service.load_categories()
category_service.load_transfer_categories()

# Import durchführen
import_service = TransactionImportService(
    api_client, config, account_service, category_service
)
stats = import_service.run_import()

print(f"Importiert: {stats.total_imported} Transaktionen")
```

## ⚙️ Konfigurationsoptionen

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `BAEZI_API_URL` | ezbookkeeping API URL | `http://192.168.176.3:8050/api/v1` |
| `BAEZI_API_TOKEN` | API Token (erforderlich!) | - |
| `BAEZI_JSON_FOLDER` | Banking4 Export-Ordner | `/mnt/c/Users/simon/b4export` |
| `BAEZI_MIN_DATE` | Mindest-Buchungsdatum (YYYY-MM-DD) | `2024-01-15` |
| `BAEZI_LOG_LEVEL` | Log-Level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `BAEZI_TIMEZONE` | Timezone | `Europe/Berlin` |
| `BAEZI_PAGE_SIZE` | API Paging-Größe | `50` |
| `BAEZI_TRANSFER_TOLERANCE_DAYS` | Transfer-Matching Toleranz in Tagen | `3` |

## 🔧 Account-Setup in ezbookkeeping

Damit Transaktionen den richtigen Konten zugeordnet werden können, müssen Sie in ezbookkeeping im **Kommentarfeld** jedes Kontos die Banking4-Account-ID hinterlegen:

```
[B4AccID:12345]
```

**So finden Sie die Banking4-Account-ID:**
- Die Account-ID ist der Dateiname des JSON-Exports (ohne `.json`)
- Z.B. `12345.json` → Account-ID ist `12345`

## 📊 Import-Prozess

Der Import läuft in 3 Phasen:

1. **Phase 1: Duplikat-Check**
   - Lädt alle bereits importierten B4-IDs aus ezbookkeeping

2. **Phase 2: Normale Transaktionen**
   - Importiert Einnahmen und Ausgaben
   - Sammelt Umbuchungen für Transfer-Matching

3. **Phase 3: Transfer-Pairing**
   - Matched zusammengehörige Umbuchungen
   - Importiert Paare als interne Transfers (Typ 4)
   - Unpaarige Umbuchungen werden als externe Transfers importiert

## 🧪 Tests

```bash
# Alle Tests ausführen
poetry run pytest

# Mit Coverage
poetry run pytest --cov

# Einzelner Test
poetry run pytest tests/test_models.py
```

## 🛠️ Entwicklung

### Code-Qualität

```bash
# Linting mit ruff
poetry run ruff check baezi/

# Auto-Fix
poetry run ruff check --fix baezi/

# Formatting
poetry run ruff format baezi/

# Type-Checking
poetry run mypy baezi/
```

### Pre-Commit Hooks

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## 📁 Projektstruktur

```
baezi/
├── baezi/
│   ├── __init__.py           # Package-Hauptmodul
│   ├── __main__.py           # CLI Entry-Point
│   ├── config.py             # Konfigurationsmanagement
│   ├── models.py             # Datenmodelle
│   ├── api/
│   │   └── client.py         # API-Client
│   ├── services/
│   │   ├── account_service.py
│   │   ├── category_service.py
│   │   └── transaction_service.py
│   ├── importers/
│   │   └── transfer_matcher.py
│   └── utils/
│       └── logging.py
├── tests/                    # Unit-Tests
├── .env.example              # Beispiel-Konfiguration
├── .gitignore
├── pyproject.toml
└── README.md
```

## 🤝 Mitwirken

Contributions sind willkommen! Bitte erstellen Sie einen Pull Request oder öffnen Sie ein Issue.

## 📝 Lizenz

MIT License - siehe LICENSE Datei

## 🙏 Danksagungen

- [ezbookkeeping](https://github.com/mayswind/ezbookkeeping) - Das großartige Budget-Management-Tool
- Banking4 - Für die Inspiration

---

**⚡ Entwickelt mit Python & ❤️**
