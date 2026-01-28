"""Tests für Config."""

import os
import pytest
from pathlib import Path

from baezi.config import Config


def test_config_from_env(monkeypatch):
    """Test Config.from_env()."""
    monkeypatch.setenv("BAEZI_API_TOKEN", "test-token")
    monkeypatch.setenv("BAEZI_API_URL", "http://test.local/api")
    monkeypatch.setenv("BAEZI_JSON_FOLDER", "/tmp/test")
    monkeypatch.setenv("BAEZI_MIN_DATE", "2024-01-01")

    config = Config.from_env()

    assert config.api_token == "test-token"
    assert config.api_base_url == "http://test.local/api"
    assert config.min_booking_date == "2024-01-01"


def test_config_from_env_missing_token(monkeypatch):
    """Test Config.from_env() ohne Token."""
    monkeypatch.delenv("BAEZI_API_TOKEN", raising=False)

    with pytest.raises(ValueError, match="BAEZI_API_TOKEN nicht gesetzt"):
        Config.from_env()


def test_config_validate_invalid_date(tmp_path):
    """Test Config.validate() mit ungültigem Datum."""
    config = Config(
        api_base_url="http://test.local",
        api_token="token",
        json_folder=tmp_path,  # Verwende tmp_path fixture
        min_booking_date="invalid-date",
    )

    with pytest.raises(ValueError, match="Ungültiges Datumsformat"):
        config.validate()
