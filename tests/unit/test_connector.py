# tests/unit/test_connector.py
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.connector import MT5Connector


@pytest.fixture
def mock_mt5(mocker):
    """Mock de mt5 module zoals geïmporteerd in src.core.connector."""
    return mocker.patch("src.core.connector.mt5")

@pytest.fixture
def connector(mock_mt5):
    """Creëer een MT5Connector instantie voor tests."""
    config = {
        "mt5_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
        "login": 12345678,
        "password": "test_password",
        "server": "Demo-Server",
    }

    connector = MT5Connector(config)
    connector.tf_map = {"H4": mock_mt5.TIMEFRAME_H4}  # Mock voor timeframe mapping
    connector.logger = MagicMock()
    connector.connected = False  # Belangrijk: start zonder verbinding
    connector.mt5 = mock_mt5  # Injecteer de gemockte mt5 module

    return connector

def test_get_historical_data(connector, mock_mt5):
    """Test het ophalen van historische data."""
    test_data = [
        {"time": 1234567890, "open": 1.1, "high": 1.11, "low": 1.09, "close": 1.10, "tick_volume": 100},
        {"time": 1234567900, "open": 1.11, "high": 1.12, "low": 1.10, "close": 1.11, "tick_volume": 110},
    ]
    mock_mt5.copy_rates_from_pos.return_value = test_data

    result = connector.get_historical_data("EURUSD", "H4", 100)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "time" in result.columns
    assert "open" in result.columns
    assert "high" in result.columns
    assert "low" in result.columns
    assert "close" in result.columns
    mock_mt5.copy_rates_from_pos.assert_called_once()

def test_get_account_info(connector, mock_mt5):
    """Test het ophalen van account informatie."""
    account_info = MagicMock()
    account_info.balance = 10000.0
    account_info.equity = 9950.0
    account_info.margin = 200.0
    account_info.margin_free = 9750.0
    account_info.margin_level = 4975.0
    account_info.currency = "USD"
    mock_mt5.account_info.return_value = account_info

    result = connector.get_account_info()

    assert result["balance"] == 10000.0
    assert result["equity"] == 9950.0
    assert result["margin"] == 200.0
    assert result["free_margin"] == 9750.0
    assert result["margin_level"] == 4975.0
    assert result["currency"] == "USD"
    mock_mt5.account_info.assert_called_once()

def test_connect_success(mock_mt5, connector):
    """Test een succesvolle verbinding met MT5."""
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True  # Mock de login-stap
    assert connector.connect() is True
    mock_mt5.initialize.assert_called_once()

def test_connect_failure(mock_mt5, connector):
    """Test een mislukte verbinding met MT5."""
    mock_mt5.initialize.return_value = False
    assert connector.connect() is False
    connector.logger.error.assert_called()

def test_place_order(mock_mt5, connector):
    """Test het plaatsen van een order."""
    # Mock alle benodigde MT5-methoden
    mock_mt5.symbol_info.return_value = MagicMock(visible=True)
    mock_mt5.symbol_info_tick.return_value = MagicMock(ask=1.1000, bid=1.0998)
    mock_mt5.order_send.return_value = MagicMock(retcode=10009, order=123)
    mock_mt5.TRADE_RETCODE_DONE = 10009  # Definieer TRADE_RETCODE_DONE expliciet

    # Zorg dat de connector verbonden is
    connector.connected = True

    result = connector.place_order(symbol="EURUSD", order_type="BUY", volume=0.1)
    assert result["success"] is True
    assert result["order_id"] == "123"