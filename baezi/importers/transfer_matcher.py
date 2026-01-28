"""Transfer-Matcher für Umbuchungen."""

import logging

from baezi.models import B4Transaction, TransferPair

logger = logging.getLogger(__name__)


class TransferMatcher:
    """Matched zusammengehörige Umbuchungen zwischen Konten."""

    def __init__(self, tolerance_days: int = 3):
        """Initialisiert Transfer-Matcher.

        Args:
            tolerance_days: Maximale Tage-Differenz zwischen Transaktionen
        """
        self.tolerance_days = tolerance_days

    def find_matches(
        self, transfers: list[B4Transaction], existing_ids: set[str]
    ) -> tuple[list[TransferPair], list[B4Transaction]]:
        """Findet zusammengehörige Umbuchungen.

        Args:
            transfers: Liste von Umbuchungs-Transaktionen
            existing_ids: Set von bereits importierten B4-IDs

        Returns:
            Tuple aus (matched_pairs, unmatched_transfers)
        """
        matches: list[TransferPair] = []
        unmatched: list[B4Transaction] = []
        processed: set[str] = set()

        for i, tx1 in enumerate(transfers):
            # Überspringe bereits verarbeitete oder existierende
            if tx1.id in processed or tx1.id in existing_ids:
                continue

            # Suche Partner
            partner = self._find_partner(tx1, transfers[i + 1 :], processed, existing_ids)

            if partner:
                # Paar gefunden
                pair = TransferPair(source_tx=tx1, dest_tx=partner)
                matches.append(pair)
                processed.update([tx1.id, partner.id])

                logger.debug(
                    f"  🔗 Paar gefunden: [B4Acc {pair.sender.account_id}] ➜ "
                    f"[B4Acc {pair.receiver.account_id}], {pair.amount}€, "
                    f"B4IDs: {pair.combined_id}"
                )
            else:
                # Kein Partner gefunden
                unmatched.append(tx1)
                processed.add(tx1.id)

        logger.info(
            f"Transfer-Matching: {len(matches)} Paare gefunden, {len(unmatched)} ohne Partner"
        )

        return matches, unmatched

    def _find_partner(
        self,
        tx: B4Transaction,
        candidates: list[B4Transaction],
        processed: set[str],
        existing_ids: set[str],
    ) -> B4Transaction | None:
        """Findet passenden Partner für Transfer.

        Args:
            tx: Transaktion für die Partner gesucht wird
            candidates: Kandidaten-Liste
            processed: Bereits verarbeitete IDs
            existing_ids: Bereits importierte IDs

        Returns:
            Partner-Transaktion oder None
        """
        for candidate in candidates:
            if candidate.id in processed or candidate.id in existing_ids:
                continue

            if self._is_match(tx, candidate):
                return candidate

        return None

    def _is_match(self, tx1: B4Transaction, tx2: B4Transaction) -> bool:
        """Prüft ob zwei Transaktionen zusammengehören.

        Bedingungen:
        - Gleicher Betrag
        - Unterschiedliche Accounts
        - Entgegengesetzte Richtung (CRDT vs DBIT)
        - Datum innerhalb Toleranz

        Args:
            tx1: Erste Transaktion
            tx2: Zweite Transaktion

        Returns:
            True wenn Transaktionen zusammengehören
        """
        return (
            tx1.amount == tx2.amount
            and tx1.account_id != tx2.account_id
            and tx1.direction != tx2.direction
            and abs((tx1.booking_date - tx2.booking_date).days) <= self.tolerance_days
        )
