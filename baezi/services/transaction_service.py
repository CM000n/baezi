"""Transaction-Import-Service."""

import json
import logging
import time as time_lib
from datetime import datetime

from baezi.api.client import APIError, EzbookkeepingClient
from baezi.config import Config
from baezi.importers.transfer_matcher import TransferMatcher
from baezi.models import B4Transaction, ImportStats, TransactionType, TransferPair
from baezi.services.account_service import AccountService
from baezi.services.category_service import CategoryService

logger = logging.getLogger(__name__)


class TransactionImportService:
    """Service für Transaction-Import von Banking4 zu ezbookkeeping."""

    def __init__(
        self,
        api_client: EzbookkeepingClient,
        config: Config,
        account_service: AccountService,
        category_service: CategoryService,
    ):
        """Initialisiert Transaction-Import-Service.

        Args:
            api_client: ezbookkeeping API-Client
            config: Konfiguration
            account_service: Account-Service
            category_service: Kategorie-Service
        """
        self.api = api_client
        self.config = config
        self.account_service = account_service
        self.category_service = category_service
        self.transfer_matcher = TransferMatcher(config.transfer_tolerance_days)
        self.stats = ImportStats()

    def run_import(self) -> ImportStats:
        """Führt vollständigen Import aus.

        Returns:
            Import-Statistik
        """
        logger.info("=" * 60)
        logger.info("🚀 B4 -> ezbookkeeping Import gestartet")
        logger.info("=" * 60)
        logger.info(f"📅 Filter: Nur Transaktionen ab {self.config.min_booking_date}")

        # Phase 1: Vorhandene IDs laden
        logger.info("📋 Phase 1: Lade existierende IDs aus ezbookkeeping...")
        existing_ids = self._load_existing_ids()

        # Phase 2: Normale Transaktionen importieren
        logger.info("📥 Phase 2: Importiere normale Transaktionen...")
        all_transfers = self._import_transactions(existing_ids)

        # Phase 3: Transfer-Pairing
        logger.info(f"🔀 Phase 3: Transfer-Pairing ({len(all_transfers)} Umbuchungen gefunden)...")
        self._import_transfers(all_transfers, existing_ids)

        # Abschluss
        self._print_summary()

        return self.stats

    def _load_existing_ids(self) -> set[str]:
        """Lädt alle bereits importierten Banking4-IDs.

        Returns:
            Set von B4-IDs
        """
        all_b4_ids = set()

        try:
            transactions = self.api.get_all_transactions()

            for tx in transactions:
                comment = tx.get("comment", "")
                if "[B4ID:" in comment:
                    # Extrahiere ID(s)
                    raw_id_str = comment.split("[B4ID:")[1].split("]")[0]
                    # Falls kombinierte Transfer-ID (ID1_ID2), splitten
                    for single_id in raw_id_str.split("_"):
                        all_b4_ids.add(single_id)

            logger.info(f"✓ Abgleich beendet. {len(all_b4_ids)} Banking4-IDs gefunden.")

        except Exception as e:
            logger.error(f"❌ Fehler beim Laden existierender IDs: {e}")

        return all_b4_ids

    def _import_transactions(self, existing_ids: set[str]) -> list[B4Transaction]:
        """Importiert normale Transaktionen (keine Transfers).

        Args:
            existing_ids: Set bereits importierter IDs

        Returns:
            Liste von Umbuchungs-Transaktionen für späteren Transfer-Match
        """
        all_transfers: list[B4Transaction] = []
        json_folder = self.config.json_folder

        for filepath in json_folder.glob("*.json"):
            b4_acc_id = filepath.stem

            # Prüfe ob Account existiert
            if not self.account_service.has_account(b4_acc_id):
                logger.warning(
                    f"⚠️  Konto mit B4AccID '{b4_acc_id}' nicht in ezbookkeeping gefunden - "
                    f"überspringe Datei"
                )
                logger.warning(
                    f"    Tipp: Erstellen Sie das Konto und fügen Sie "
                    f"'[B4AccID:{b4_acc_id}]' im Kommentarfeld hinzu"
                )
                continue

            acc_id = self.account_service.get_ezb_account_id(b4_acc_id)
            logger.info(f"  📂 Verarbeite Konto: B4AccID {b4_acc_id} (ezb-ID: {acc_id})")

            # Lade und verarbeite Transaktionen
            with open(filepath, encoding="utf-8") as f:
                transactions_json = json.load(f)

            for tx_data in transactions_json:
                # Überspringe vorgemerkte Transaktionen (haben kein BookgDt)
                if tx_data.get("BookgSts") != "BOOK":
                    continue

                try:
                    tx = B4Transaction.from_json(tx_data, b4_acc_id)
                except ValueError as e:
                    logger.error(f"    ❌ Fehler beim Parsen der Transaktion: {e}")
                    logger.debug(f"       Rohdaten: {tx_data}")
                    self.stats.increment_errors()
                    continue

                # Datumsfilter anwenden
                if tx.booking_date.strftime("%Y-%m-%d") < self.config.min_booking_date:
                    continue

                if tx.id in existing_ids:
                    self.stats.increment_skipped()
                    continue

                # Umbuchungen sammeln für späteren Transfer-Match
                if tx.is_transfer:
                    all_transfers.append(tx)
                    logger.debug(
                        f"    🔄 Umbuchung gesammelt: B4ID {tx.id}, {tx.amount}€ "
                        f"({tx.direction.value})"
                    )
                else:
                    # Normale Transaktion importieren
                    self._import_single_transaction(tx, acc_id, existing_ids)

        return all_transfers

    def _import_single_transaction(
        self, tx: B4Transaction, acc_id: str, existing_ids: set[str]
    ) -> bool:
        """Importiert einzelne Transaktion.

        Args:
            tx: B4-Transaktion
            acc_id: ezbookkeeping Account-ID
            existing_ids: Set bereits importierter IDs

        Returns:
            True wenn erfolgreich importiert
        """
        try:
            # Kategorie sicherstellen
            cat_id = self.category_service.ensure_category_hierarchy(
                tx.category, tx.transaction_type.value, self.stats
            )

            # Payload erstellen
            payload = self._create_transaction_payload(
                acc_id=acc_id,
                amount=tx.amount,
                booking_date=tx.booking_date,
                description=tx.description,
                category_id=cat_id,
                transaction_type=tx.transaction_type,
                b4_id=tx.id,
            )

            # Import
            resp = self.api.create_transaction(payload)

            if resp.get("success"):
                existing_ids.add(tx.id)
                self.stats.increment_transactions()
                logger.debug(f"    ✓ Transaktion importiert: B4ID {tx.id}, {tx.amount}€")
                return True
            logger.error(f"    ❌ Fehler bei B4ID {tx.id}: {resp}")
            self.stats.increment_errors()
            return False

        except APIError as e:
            logger.error(f"    ❌ API-Fehler bei B4ID {tx.id}: {e}")
            self.stats.increment_errors()
            return False

    def _import_transfers(self, transfers: list[B4Transaction], existing_ids: set[str]) -> None:
        """Importiert Transfers (Umbuchungen).

        Args:
            transfers: Liste von Umbuchungs-Transaktionen
            existing_ids: Set bereits importierter IDs
        """
        # Finde Paare
        matched_pairs, unmatched = self.transfer_matcher.find_matches(transfers, existing_ids)

        # Importiere gematchte Paare
        for pair in matched_pairs:
            self._import_transfer_pair(pair, existing_ids)

        # Importiere unpaarige als normale Transaktionen mit externer Kategorie
        for tx in unmatched:
            self._import_unmatched_transfer(tx, existing_ids)

    def _import_transfer_pair(self, pair: TransferPair, existing_ids: set[str]) -> bool:
        """Importiert Transfer-Paar.

        Args:
            pair: Transfer-Paar
            existing_ids: Set bereits importierter IDs

        Returns:
            True wenn erfolgreich
        """
        try:
            sender_acc_id = self.account_service.get_ezb_account_id(pair.sender.account_id)
            receiver_acc_id = self.account_service.get_ezb_account_id(pair.receiver.account_id)

            logger.info(
                f"  🔗 Paar gefunden: [B4Acc {pair.sender.account_id}] ➜ "
                f"[B4Acc {pair.receiver.account_id}], {pair.amount}€, "
                f"B4IDs: {pair.combined_id}"
            )

            payload = self._create_transaction_payload(
                acc_id=sender_acc_id,
                amount=pair.amount,
                booking_date=pair.date,
                description=f"Transfer: {pair.sender.description[:100]}",
                category_id=self.category_service.transfer_category_id,
                transaction_type=TransactionType.TRANSFER,
                b4_id=pair.combined_id,
                partner_acc_id=receiver_acc_id,
            )

            resp = self.api.create_transaction(payload)

            if resp.get("success"):
                existing_ids.update([pair.source_tx.id, pair.dest_tx.id])
                self.stats.increment_transfers()
                logger.info("    ✓ Transfer importiert")
                return True
            logger.error(f"    ❌ Transfer-Import fehlgeschlagen: {resp}")
            self.stats.increment_errors()
            return False

        except APIError as e:
            logger.error(f"    ❌ Transfer-Import fehlgeschlagen: {e}")
            self.stats.increment_errors()
            return False

    def _import_unmatched_transfer(self, tx: B4Transaction, existing_ids: set[str]) -> bool:
        """Importiert unpaarige Umbuchung als normale Transaktion.

        Args:
            tx: Unpaarige Umbuchungs-Transaktion
            existing_ids: Set bereits importierter IDs

        Returns:
            True wenn erfolgreich
        """
        acc_id = self.account_service.get_ezb_account_id(tx.account_id)
        trans_type = tx.transaction_type
        trans_type_name = "Einnahme" if tx.is_income else "Ausgabe"

        # Verwende externe Transfer-Kategorie
        ext_cat_id = self.category_service.get_external_transfer_category(tx.is_income)

        logger.warning(
            f"  ⚠️  Kein Partner gefunden für B4ID {tx.id} "
            f"(B4Acc {tx.account_id}, {tx.amount}€) - "
            f"als {trans_type_name} mit externer Transfer-Kategorie importiert"
        )

        try:
            payload = self._create_transaction_payload(
                acc_id=acc_id,
                amount=tx.amount,
                booking_date=tx.booking_date,
                description=f"[Extern] {tx.description}",
                category_id=ext_cat_id,
                transaction_type=trans_type,
                b4_id=tx.id,
            )

            resp = self.api.create_transaction(payload)

            if resp.get("success"):
                self.stats.increment_transactions()
                return True
            logger.error(f"    ❌ Import fehlgeschlagen: {resp}")
            self.stats.increment_errors()
            return False

        except APIError as e:
            logger.error(f"    ❌ Import fehlgeschlagen: {e}")
            self.stats.increment_errors()
            return False

    def _create_transaction_payload(
        self,
        acc_id: str,
        amount: float,
        booking_date: datetime,
        description: str,
        category_id: str,
        transaction_type: TransactionType,
        b4_id: str,
        partner_acc_id: str = "0",
    ) -> dict:
        """Erstellt Payload für Transaktions-API.

        Args:
            acc_id: ezbookkeeping Account-ID
            amount: Betrag
            booking_date: Buchungsdatum
            description: Beschreibung
            category_id: Kategorie-ID
            transaction_type: Transaktionstyp
            b4_id: Banking4 ID
            partner_acc_id: Partner Account-ID (für Transfers)

        Returns:
            API-Payload Dictionary
        """
        amt_cents = int(round(abs(float(amount)) * 100))

        # Kommentar auf 200 Zeichen begrenzen
        clean_desc = description[:200]
        final_comment = f"{clean_desc} [B4ID:{b4_id}]"

        # Für Transfers immer richtige Transfer-Kategorie verwenden
        if (
            transaction_type == TransactionType.TRANSFER
            and self.category_service.transfer_category_id != "0"
        ):
            category_id = self.category_service.transfer_category_id

        # UTC Offset berechnen
        utc_offset = self._get_utc_offset_minutes()

        payload = {
            "type": transaction_type.value,
            "time": int(booking_date.timestamp()),
            "utcOffset": utc_offset,
            "categoryId": str(category_id),
            "tagIds": [],
            "comment": final_comment,
        }

        if transaction_type == TransactionType.TRANSFER:
            payload.update(
                {
                    "sourceAccountId": str(acc_id),
                    "destinationAccountId": str(partner_acc_id),
                    "sourceAmount": amt_cents,
                    "destinationAmount": amt_cents,
                }
            )
        else:
            payload.update({"sourceAccountId": str(acc_id), "sourceAmount": amt_cents})

        return payload

    def _get_utc_offset_minutes(self) -> int:
        """Berechnet UTC-Offset in Minuten."""
        if time_lib.localtime().tm_isdst and time_lib.daylight:
            return -int(time_lib.altzone / 60)
        return -int(time_lib.timezone / 60)

    def _print_summary(self) -> None:
        """Gibt Import-Zusammenfassung aus."""
        logger.info("=" * 60)
        logger.info("✅ Import abgeschlossen!")
        logger.info("=" * 60)
        logger.info("📊 Statistik:")
        logger.info(f"   ✓ Neue Transaktionen: {self.stats.new_transactions}")
        logger.info(f"   ✓ Neue Transfers: {self.stats.new_transfers}")
        logger.info(f"   ✓ Neue Kategorien: {self.stats.new_categories}")
        logger.info(f"   ⏭️  Übersprungen: {self.stats.skipped}")
        if self.stats.errors > 0:
            logger.info(f"   ❌ Fehler: {self.stats.errors}")
        logger.info("📝 Detailliertes Log: baezi_import.log")
