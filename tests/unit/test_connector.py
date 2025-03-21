# tests/unit/test_connector.py
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.connector import MT5Connector


@pytest.fixture
def connector(mock_mt5):
    """Creëer een MT5Connector instantie voor tests."""
    config = {"mt5_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
              "login": 12345678, "password": "test_password", "server": "Demo-Server", }

    connector = MT5Connector(config)
    connector.tf_map = {"H4": mock_mt5.TIMEFRAME_H4}  # Mock voor timeframe mapping
    connector.logger = MagicMock()
    connector.connected = True

    return connector


def test_get_historical_data(connector, mock_mt5):
    """Test het ophalen van historische data."""
    # Cruciale fix: Injecteer de mock direct in de testfunctie
    connector.mt5 = mock_mt5

    # Mock de MT5 response voor copy_rates_from_pos
    test_data = [
        {"time": 1234567890, "open": 1.1, "high": 1.11, "low": 1.09, "close": 1.10,
         "tick_volume": 100, },
        {"time": 1234567900, "open": 1.11, "high": 1.12, "low": 1.10, "close": 1.11,
         "tick_volume": 110, }, ]
    mock_mt5.copy_rates_from_pos.return_value = test_data

    # Test de functie
    result = connector.get_historical_data("EURUSD", "H4", 100)

    # Controleer of het resultaat correct is
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2  # Twee rijen in onze mock data
    assert "time" in result.columns
    assert "open" in result.columns
    assert "high" in result.columns
    assert "low" in result.columns
    assert "close" in result.columns

    # Verifieer dat de MT5 functie correct is aangeroepen
    mock_mt5.copy_rates_from_pos.assert_called_once()
    args = mock_mt5.copy_rates_from_pos.call_args[0]
    assert args[0] == "EURUSD"  # Verificeer het symbool
    assert args[2] == 0  # Verificeer de positie
    assert args[3] == 100  # Verificeer aantal bars


def test_get_account_info(connector, mock_mt5):
    """Test het ophalen van account informatie."""
    # Cruciale fix: Injecteer de mock direct in de testfunctie
    connector.mt5 = mock_mt5

    # Setup mock account info
    account_info = MagicMock()
    account_info.balance = 10000.0
    account_info.equity = 9950.0
    account_info.margin = 200.0
    account_info.margin_free = 9750.0
    account_info.margin_level = 4975.0
    account_info.currency = "USD"
    mock_mt5.account_info.return_value = account_info

    # Test de functie
    result = connector.get_account_info()

    # Controleer of het resultaat correct is
    assert result["balance"] == 10000.0
    assert result["equity"] == 9950.0
    assert result["margin"] == 200.0
    assert result["free_margin"] == 9750.0
    assert result["margin_level"] == 4975.0
    assert result["currency"] == "USD"

    # Verifieer dat de MT5 functie correct is aangeroepen
    mock_mt5.account_info.assert_called_once()
