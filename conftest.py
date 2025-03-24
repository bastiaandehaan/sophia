# conftest.py (in project root: C:\Users\Gebruiker\PycharmProjects\Sophia\)
import os
import sys
import time
from datetime import datetime
from subprocess import Popen
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

print("Loading test fixtures from conftest.py")  # Debug-regel

# Zorg dat de projectroot in sys.path staat
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


# Registreer custom markers
def pytest_configure(config):
    """Registreer custom markers."""
    config.addinivalue_line("markers", "unit: mark a test as a unit test")
    config.addinivalue_line("markers",
                            "integration: mark a test as an integration test")
    config.addinivalue_line("markers",
                            "e2e: mark a test as an end-to-end test (voor Playwright)")

    # Playwright-specifieke configuratie
    if "e2e" in config.getoption("-m", default=""):
        config.option.browser = "chromium"
        config.option.headed = True


# Fixture om Streamlit te starten voor e2e-tests
@pytest.fixture(scope="session")
def start_streamlit_server():
    """Start de Streamlit-server voor end-to-end tests."""
    process = Popen(["streamlit", "run", "src/backtesting/dashboard.py"])
    time.sleep(5)  # Wacht tot de server opstart
    yield
    process.terminate()  # Sluit na alle tests


@pytest.fixture
def logger_fixture():
    """Creëer een logger mock voor tests."""
    logger_mock = MagicMock()
    logger_mock.info = MagicMock()
    logger_mock.error = MagicMock()
    logger_mock.warning = MagicMock()
    logger_mock.debug = MagicMock()
    logger_mock.log_info = MagicMock()  # Voor backward compatibility
    return logger_mock


@pytest.fixture
def sample_ohlc_data():
    """Genereer een sample OHLC DataFrame voor tests."""
    dates = pd.date_range(start="2023-01-01", periods=100)
    data = pd.DataFrame(
        {
            "open": np.linspace(1.0, 1.1, 100),
            "high": np.linspace(1.01, 1.11, 100),
            "low": np.linspace(0.99, 1.09, 100),
            "close": np.linspace(1.005, 1.105, 100),
            "time": dates,
        }
    )
    # Voeg een breakout toe om signalen te triggeren
    data.loc[data.index[-10:], "high"] *= 1.02
    data.loc[data.index[-10:], "close"] *= 1.01
    return data


@pytest.fixture
def mock_mt5():
    """Creëer een mock voor de MetaTrader5 module."""
    mt5_mock = MagicMock()
    mt5_mock.initialize.return_value = True
    mt5_mock.login.return_value = True
    mt5_mock.shutdown.return_value = True
    mock_rates = [
        {"time": 1234567890, "open": 1.1, "high": 1.11, "low": 1.09,
         "close": 1.10, "tick_volume": 100},
        {"time": 1234567900, "open": 1.11, "high": 1.12, "low": 1.10,
         "close": 1.11, "tick_volume": 110},
    ]
    mt5_mock.copy_rates_from_pos.return_value = mock_rates
    account_info_mock = MagicMock()
    account_info_mock.balance = 10000.0
    account_info_mock.equity = 10000.0
    account_info_mock.margin = 0.0
    account_info_mock.free_margin = 10000.0
    account_info_mock.margin_level = 0.0
    account_info_mock.leverage = 30
    account_info_mock.currency = "USD"
    mt5_mock.account_info.return_value = account_info_mock
    mt5_mock.TIMEFRAME_M1 = 1
    mt5_mock.TIMEFRAME_M5 = 5
    mt5_mock.TIMEFRAME_M15 = 15
    mt5_mock.TIMEFRAME_H1 = 60
    mt5_mock.TIMEFRAME_H4 = 240
    mt5_mock.TIMEFRAME_D1 = 1440
    mt5_mock.ORDER_TYPE_BUY = 0
    mt5_mock.ORDER_TYPE_SELL = 1
    mt5_mock.last_error.return_value = 0
    return mt5_mock


@pytest.fixture
def connector(mock_mt5):
    """Creëer een MT5Connector instantie voor tests."""
    from src.core.connector import MT5Connector  # Pas aan naar je echte import
    config = {
        "mt5_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
        "login": 12345678,
        "password": "test_password",
        "server": "Demo-Server",
    }
    connector = MT5Connector(config)
    connector.tf_map = {"H4": mock_mt5.TIMEFRAME_H4}
    connector.mt5 = mock_mt5
    connector.logger = MagicMock()
    connector.connected = True
    return connector


@pytest.fixture
def mock_connector():
    """Creëer een mock voor MT5Connector."""
    connector_mock = MagicMock()
    connector_mock.connect.return_value = True
    connector_mock.disconnect.return_value = True

    def get_mock_data(symbol, timeframe, bars_count=100):
        dates = pd.date_range(end=datetime.now(), periods=bars_count)
        data = pd.DataFrame(
            {
                "open": np.linspace(1.1, 1.2, bars_count),
                "high": np.linspace(1.12, 1.22, bars_count),
                "low": np.linspace(1.09, 1.19, bars_count),
                "close": np.linspace(1.11, 1.21, bars_count),
                "time": dates,
            }
        )
        data.loc[data.index[-10:], "high"] *= 1.02
        data.loc[data.index[-10:], "close"] *= 1.01
        return data

    connector_mock.get_historical_data.side_effect = get_mock_data
    connector_mock.get_account_info.return_value = {
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 0.0,
        "free_margin": 10000.0,
        "margin_level": 0.0,
        "currency": "USD",
    }
    connector_mock.place_order.return_value = {
        "success": True,
        "order_id": "12345",
        "symbol": "EURUSD",
        "type": "BUY",
        "volume": 0.1,
        "price": 1.2000,
        "sl": 1.1950,
    }
    connector_mock.get_position.return_value = {
        "symbol": "EURUSD",
        "direction": "BUY",
        "volume": 0.1,
        "open_price": 1.2000,
        "current_price": 1.2100,
        "profit": 100.0,
        "sl": 1.1950,
    }
    return connector_mock


@pytest.fixture
def mock_risk_manager():
    """Creëer een mock voor RiskManager."""
    risk_manager_mock = MagicMock()
    risk_manager_mock.calculate_position_size.return_value = 0.1
    risk_manager_mock.is_trading_allowed = True
    return risk_manager_mock


@pytest.fixture
def test_config():
    """Standaard test configuratie."""
    return {
        "mt5": {
            "login": 12345678,
            "password": "test_password",
            "server": "Demo-Server",
            "mt5_path": "C:\\Program Files\\FTMO Global Markets MT5 Terminal\\terminal64.exe",
        },
        "symbols": ["EURUSD", "GBPUSD"],
        "timeframe": "H4",
        "interval": 300,
        "risk": {"risk_per_trade": 0.01, "max_daily_loss": 0.05},
        "strategy": {"entry_period": 20, "exit_period": 10, "atr_period": 14},
    }