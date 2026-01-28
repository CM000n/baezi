"""Pytest Konfiguration und Fixtures."""

import pytest

from baezi.config import Config
from baezi.models import B4Transaction, Direction, BookingStatus
from datetime import datetime


@pytest.fixture
def mock_config():
    """Mock Config für Tests."""
    return Config(
        api_base_url="http://localhost:8050/api/v1",
        api_token="test-token",
        json_folder="/tmp/test",
        min_booking_date="2024-01-01",
        log_level="DEBUG",
    )


@pytest.fixture
def sample_b4_transaction():
    """Sample B4Transaction für Tests."""
    return B4Transaction(
        id="12345",
        booking_date=datetime(2024, 1, 15),
        amount=100.50,
        description="Test Transaction",
        direction=Direction.CREDIT,
        category="Einkommen:Gehalt",
        booking_status=BookingStatus.BOOKED,
        account_id="ACC001",
    )
