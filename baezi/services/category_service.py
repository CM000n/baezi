"""Kategorie-Service für ezbookkeeping Kategorien."""

import logging

from baezi.api.client import EzbookkeepingClient
from baezi.models import ImportStats

logger = logging.getLogger(__name__)


class CategoryService:
    """Service für Kategorie-Management."""

    def __init__(self, api_client: EzbookkeepingClient):
        """Initialisiert Kategorie-Service.

        Args:
            api_client: ezbookkeeping API-Client
        """
        self.api = api_client
        self._category_map: dict[str, str] = {}
        self._transfer_category_id: str = "0"
        self._external_transfer_cats: dict[str, str] = {"income": "0", "expense": "0"}

    def load_categories(self) -> dict[str, str]:
        """Lädt alle Kategorien und erstellt Mapping.

        Returns:
            Dictionary: "type_name" oder "type_name:subname" -> ID
        """
        logger.info("Lade Kategorien...")

        resp = self.api.get_categories()

        if not resp.get("success"):
            logger.warning("⚠️  Konnte Kategorien nicht laden")
            return {}

        cat_map = {}

        for c_type_str, categories in resp["result"].items():
            c_type = int(c_type_str)

            for main in categories:
                main_key = f"{c_type}_{main['name']}"
                cat_map[main_key] = main["id"]

                for sub in main.get("subCategories", []):
                    sub_key = f"{c_type}_{main['name']}:{sub['name']}"
                    cat_map[sub_key] = sub["id"]

        self._category_map = cat_map
        logger.info(f"✓ {len(cat_map)} Kategorien geladen")

        return cat_map

    def load_transfer_categories(self) -> None:
        """Lädt Transfer-Kategorien für interne und externe Transfers."""
        # Interne Transfers (Typ 4)
        self._transfer_category_id = self._find_transfer_category()

        if self._transfer_category_id != "0":
            logger.info(
                f"✓ Transfer-Kategorie 'Banküberweisung' geladen (ID: {self._transfer_category_id})"
            )
        else:
            logger.warning("⚠️  Transfer-Kategorie nicht gefunden - Transfers könnten fehlschlagen")

        # Externe Transfers (Typ 2/3)
        self._external_transfer_cats = self._find_external_transfer_categories()

        if (
            self._external_transfer_cats["income"] != "0"
            and self._external_transfer_cats["expense"] != "0"
        ):
            logger.info(
                f"✓ Externe Transfer-Kategorien geladen "
                f"(Einnahme: {self._external_transfer_cats['income']}, "
                f"Ausgabe: {self._external_transfer_cats['expense']})"
            )
        else:
            logger.warning("⚠️  Externe Transfer-Kategorien nicht vollständig gefunden")

    def _find_transfer_category(self) -> str:
        """Findet 'Banküberweisung' Kategorie für interne Transfers."""
        resp = self.api.get_categories()

        if not resp.get("success"):
            return "0"

        for c_type_str, categories in resp["result"].items():
            for main in categories:
                if "allgemein" in main["name"].lower() and "transfer" in main["name"].lower():
                    for sub in main.get("subCategories", []):
                        if "bank" in sub["name"].lower() and "weisung" in sub["name"].lower():
                            if "extern" not in sub["name"].lower():
                                logger.debug(
                                    f"✓ Transfer-Kategorie gefunden: "
                                    f"{main['name']} → {sub['name']} (ID: {sub['id']})"
                                )
                                return sub["id"]

        return "0"

    def _find_external_transfer_categories(self) -> dict[str, str]:
        """Findet 'Banküberweisung (extern)' Kategorien."""
        resp = self.api.get_categories()

        if not resp.get("success"):
            return {"income": "0", "expense": "0"}

        result = {"income": "0", "expense": "0"}

        for c_type_str, categories in resp["result"].items():
            c_type = int(c_type_str)

            for main in categories:
                if "allgemein" in main["name"].lower() and "transfer" in main["name"].lower():
                    for sub in main.get("subCategories", []):
                        if "extern" in sub["name"].lower() and "bank" in sub["name"].lower():
                            if c_type == 1:  # Income
                                result["income"] = sub["id"]
                                logger.debug(
                                    f"✓ Externe Transfer-Kategorie (Einnahme) gefunden: "
                                    f"{main['name']} → {sub['name']} (ID: {sub['id']})"
                                )
                            elif c_type == 2:  # Expense
                                result["expense"] = sub["id"]
                                logger.debug(
                                    f"✓ Externe Transfer-Kategorie (Ausgabe) gefunden: "
                                    f"{main['name']} → {sub['name']} (ID: {sub['id']})"
                                )

        return result

    def ensure_category_hierarchy(self, full_path: str, trans_type: int, stats: ImportStats) -> str:
        """Stellt sicher dass Kategorie-Hierarchie existiert, erstellt falls nötig.

        Args:
            full_path: Kategorie-Pfad (z.B. "Essen:Restaurant")
            trans_type: Transaktionstyp (2=Income, 3=Expense)
            stats: Import-Statistik zum Tracken neuer Kategorien

        Returns:
            Kategorie-ID
        """
        if not full_path or full_path == "Umbuchung":
            return "0"

        cat_type = 1 if trans_type == 2 else 2  # 1=Income, 2=Expense
        parts = [p.strip() for p in full_path.split(":")]
        main_name = parts[0]
        main_key = f"{cat_type}_{main_name}"

        # Hauptkategorie erstellen falls nicht vorhanden
        if main_key not in self._category_map:
            payload = {
                "name": main_name,
                "type": cat_type,
                "parentId": "0",
                "icon": "1",
                "color": "8e8e93",
            }

            try:
                res = self.api.create_category(payload)
                if res.get("success"):
                    self._category_map[main_key] = res["result"]["id"]
                    stats.increment_categories()
                    logger.debug(f"✓ Hauptkategorie erstellt: {main_name}")
                else:
                    return "0"
            except Exception as e:
                logger.error(f"❌ Fehler beim Erstellen von Kategorie {main_name}: {e}")
                return "0"

        parent_id = self._category_map[main_key]

        # Subkategorie erstellen falls vorhanden
        if len(parts) > 1:
            sub_name = parts[1]
            sub_key = f"{cat_type}_{main_name}:{sub_name}"

            if sub_key not in self._category_map:
                payload = {
                    "name": sub_name,
                    "type": cat_type,
                    "parentId": parent_id,
                    "icon": "1",
                    "color": "8e8e93",
                }

                try:
                    res = self.api.create_category(payload)
                    if res.get("success"):
                        self._category_map[sub_key] = res["result"]["id"]
                        stats.increment_categories()
                        logger.debug(f"✓ Subkategorie erstellt: {main_name}:{sub_name}")
                    else:
                        return parent_id
                except Exception as e:
                    logger.error(f"❌ Fehler beim Erstellen von Subkategorie {sub_name}: {e}")
                    return parent_id

            return self._category_map[sub_key]

        return parent_id

    @property
    def transfer_category_id(self) -> str:
        """Gibt Transfer-Kategorie-ID zurück."""
        return self._transfer_category_id

    def get_external_transfer_category(self, is_income: bool) -> str:
        """Gibt externe Transfer-Kategorie-ID zurück.

        Args:
            is_income: True für Einnahme, False für Ausgabe

        Returns:
            Kategorie-ID
        """
        return (
            self._external_transfer_cats["income"]
            if is_income
            else self._external_transfer_cats["expense"]
        )
