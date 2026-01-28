"""Tests für Datenmodelle."""

from datetime import datetime

from baezi.models import B4Transaction, BookingStatus, Direction, TransactionType, TransferPair


def test_b4_transaction_from_json():
    """Test B4Transaction.from_json()."""
    data = {
        "Id": "123",
        "BookgDt": "2024-01-15",
        "Amt": "100.50",
        "RmtInf": "Test",
        "CdtDbtInd": "CRDT",
        "Category": "Einkommen",
        "BookgSts": "BOOK",
    }

    tx = B4Transaction.from_json(data, "ACC001")

    assert tx.id == "123"
    assert tx.amount == 100.50
    assert tx.description == "Test"
    assert tx.direction == Direction.CREDIT
    assert tx.is_booked
    assert tx.is_income


def test_b4_transaction_is_transfer():
    """Test B4Transaction.is_transfer."""
    tx = B4Transaction(
        id="1",
        booking_date=datetime.now(),
        amount=100.0,
        description="Test",
        direction=Direction.DEBIT,
        category="Umbuchung",
        booking_status=BookingStatus.BOOKED,
        account_id="ACC001",
    )

    assert tx.is_transfer
    assert tx.transaction_type == TransactionType.TRANSFER


def test_transfer_pair():
    """Test TransferPair."""
    tx1 = B4Transaction(
        id="1",
        booking_date=datetime(2024, 1, 15),
        amount=100.0,
        description="Transfer out",
        direction=Direction.DEBIT,
        category="Umbuchung",
        booking_status=BookingStatus.BOOKED,
        account_id="ACC001",
    )

    tx2 = B4Transaction(
        id="2",
        booking_date=datetime(2024, 1, 16),
        amount=100.0,
        description="Transfer in",
        direction=Direction.CREDIT,
        category="Umbuchung",
        booking_status=BookingStatus.BOOKED,
        account_id="ACC002",
    )

    pair = TransferPair(source_tx=tx1, dest_tx=tx2)

    assert pair.sender == tx1
    assert pair.receiver == tx2
    assert pair.combined_id == "1_2"
    assert pair.amount == 100.0
    assert pair.date == datetime(2024, 1, 15)
