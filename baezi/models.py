"""Datenmodelle für baezi."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TransactionType(Enum):
    """ezbookkeeping Transaktionstypen."""

    INCOME = 2
    EXPENSE = 3
    TRANSFER = 4


class Direction(Enum):
    """Banking4 Transaktionsrichtung."""

    CREDIT = "CRDT"
    DEBIT = "DBIT"


class BookingStatus(Enum):
    """Banking4 Buchungsstatus."""

    BOOKED = "BOOK"
    PENDING = "PDNG"


@dataclass
class B4Transaction:
    """Banking4 Transaction Model."""

    id: str
    booking_date: datetime
    amount: float
    description: str
    direction: Direction
    category: str
    booking_status: BookingStatus
    account_id: str

    @classmethod
    def from_json(cls, data: dict, account_id: str) -> "B4Transaction":
        """Erstellt B4Transaction aus Banking4 JSON.

        Args:
            data: Banking4 JSON Daten
            account_id: Banking4 Account ID

        Returns:
            B4Transaction Instanz

        Raises:
            ValueError: Wenn erforderliche Felder fehlen
        """
        # Prüfe erforderliche Felder
        required_fields = ["Id", "BookgDt", "Amt", "RmtInf", "CdtDbtInd"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            raise ValueError(
                f"Fehlende Pflichtfelder in Transaktion: {missing_fields}. "
                f"Vorhandene Felder: {list(data.keys())}"
            )

        try:
            return cls(
                id=str(data["Id"]),
                booking_date=datetime.strptime(data["BookgDt"], "%Y-%m-%d"),
                amount=abs(float(data["Amt"])),
                description=data["RmtInf"],
                direction=Direction(data["CdtDbtInd"]),
                category=data.get("Category", ""),
                booking_status=BookingStatus(data.get("BookgSts", "BOOK")),
                account_id=account_id,
            )
        except ValueError as e:
            raise ValueError(
                f"Fehler beim Parsen der Transaktion ID {data.get('Id', 'UNKNOWN')}: {e}"
            ) from e

    @property
    def is_booked(self) -> bool:
        """Prüft ob Transaktion gebucht ist."""
        return self.booking_status == BookingStatus.BOOKED

    @property
    def is_transfer(self) -> bool:
        """Prüft ob Transaktion eine Umbuchung ist."""
        return self.category == "Umbuchung"

    @property
    def transaction_type(self) -> TransactionType:
        """Ermittelt ezbookkeeping Transaktionstyp."""
        if self.is_transfer:
            return TransactionType.TRANSFER
        return (
            TransactionType.INCOME
            if self.direction == Direction.CREDIT
            else TransactionType.EXPENSE
        )

    @property
    def is_income(self) -> bool:
        """Prüft ob Transaktion eine Einnahme ist."""
        return self.direction == Direction.CREDIT

    @property
    def is_expense(self) -> bool:
        """Prüft ob Transaktion eine Ausgabe ist."""
        return self.direction == Direction.DEBIT


@dataclass
class TransferPair:
    """Paar von zusammengehörigen Umbuchungen."""

    source_tx: B4Transaction
    dest_tx: B4Transaction

    @property
    def sender(self) -> B4Transaction:
        """Gibt Sender-Transaktion zurück."""
        return self.source_tx if self.source_tx.direction == Direction.DEBIT else self.dest_tx

    @property
    def receiver(self) -> B4Transaction:
        """Gibt Empfänger-Transaktion zurück."""
        return self.dest_tx if self.dest_tx.direction == Direction.CREDIT else self.source_tx

    @property
    def combined_id(self) -> str:
        """Kombinierte ID für Transfer."""
        return f"{self.source_tx.id}_{self.dest_tx.id}"

    @property
    def amount(self) -> float:
        """Transfer-Betrag."""
        return self.source_tx.amount

    @property
    def date(self) -> datetime:
        """Frühestes Datum der beiden Transaktionen."""
        return min(self.source_tx.booking_date, self.dest_tx.booking_date)


@dataclass
class ImportStats:
    """Statistiken für den Import."""

    skipped: int = 0
    new_transactions: int = 0
    new_transfers: int = 0
    new_categories: int = 0
    errors: int = 0

    def increment_skipped(self) -> None:
        """Erhöht Anzahl übersprungener Transaktionen."""
        self.skipped += 1

    def increment_transactions(self) -> None:
        """Erhöht Anzahl neuer Transaktionen."""
        self.new_transactions += 1

    def increment_transfers(self) -> None:
        """Erhöht Anzahl neuer Transfers."""
        self.new_transfers += 1

    def increment_categories(self) -> None:
        """Erhöht Anzahl neuer Kategorien."""
        self.new_categories += 1

    def increment_errors(self) -> None:
        """Erhöht Anzahl Fehler."""
        self.errors += 1

    @property
    def total_imported(self) -> int:
        """Gesamtanzahl importierter Items."""
        return self.new_transactions + self.new_transfers


@dataclass
class Account:
    """ezbookkeeping Account Model."""

    id: str
    name: str
    b4_account_id: str | None = None
    comment: str = ""

    @classmethod
    def from_api_response(cls, data: dict) -> "Account":
        """Erstellt Account aus API-Response.

        Args:
            data: ezbookkeeping API Daten

        Returns:
            Account Instanz
        """
        comment = data.get("comment", "")
        b4_acc_id = None

        # Extrahiere B4AccID aus Kommentar
        if "[B4AccID:" in comment:
            start = comment.find("[B4AccID:") + 9
            end = comment.find("]", start)
            if end > start:
                b4_acc_id = comment[start:end]

        return cls(
            id=data["id"], name=data.get("name", ""), b4_account_id=b4_acc_id, comment=comment
        )


@dataclass
class Category:
    """ezbookkeeping Category Model."""

    id: str
    name: str
    type: int
    parent_id: str = "0"
    full_path: str = ""

    @property
    def is_income(self) -> bool:
        """Prüft ob Einnahme-Kategorie."""
        return self.type == 1

    @property
    def is_expense(self) -> bool:
        """Prüft ob Ausgabe-Kategorie."""
        return self.type == 2
