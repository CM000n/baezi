"""Tests für Transfer-Matcher."""

from datetime import datetime

from baezi.importers.transfer_matcher import TransferMatcher
from baezi.models import B4Transaction, BookingStatus, Direction


def test_find_matches():
    """Test TransferMatcher.find_matches()."""
    matcher = TransferMatcher(tolerance_days=3)

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
        booking_date=datetime(2024, 1, 15),
        amount=100.0,
        description="Transfer in",
        direction=Direction.CREDIT,
        category="Umbuchung",
        booking_status=BookingStatus.BOOKED,
        account_id="ACC002",
    )

    tx3 = B4Transaction(
        id="3",
        booking_date=datetime(2024, 1, 20),
        amount=50.0,
        description="No match",
        direction=Direction.DEBIT,
        category="Umbuchung",
        booking_status=BookingStatus.BOOKED,
        account_id="ACC001",
    )

    transfers = [tx1, tx2, tx3]
    matches, unmatched = matcher.find_matches(transfers, set())

    assert len(matches) == 1
    assert len(unmatched) == 1
    assert matches[0].sender == tx1
    assert matches[0].receiver == tx2
    assert unmatched[0] == tx3


def test_is_match():
    """Test TransferMatcher._is_match()."""
    matcher = TransferMatcher(tolerance_days=3)

    tx1 = B4Transaction(
        id="1",
        booking_date=datetime(2024, 1, 15),
        amount=100.0,
        description="Transfer",
        direction=Direction.DEBIT,
        category="Umbuchung",
        booking_status=BookingStatus.BOOKED,
        account_id="ACC001",
    )

    tx2 = B4Transaction(
        id="2",
        booking_date=datetime(2024, 1, 17),  # 2 Tage Differenz
        amount=100.0,
        description="Transfer",
        direction=Direction.CREDIT,
        category="Umbuchung",
        booking_status=BookingStatus.BOOKED,
        account_id="ACC002",
    )

    tx3 = B4Transaction(
        id="3",
        booking_date=datetime(2024, 1, 20),  # 5 Tage Differenz (zu viel)
        amount=100.0,
        description="Transfer",
        direction=Direction.CREDIT,
        category="Umbuchung",
        booking_status=BookingStatus.BOOKED,
        account_id="ACC003",
    )

    assert matcher._is_match(tx1, tx2)
    assert not matcher._is_match(tx1, tx3)
