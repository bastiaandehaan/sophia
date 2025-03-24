# File: tests/test_main.py

import os

import pytest

from src.main import SophiaTrader


@pytest.fixture
def temp_config_file(tmp_path):
    config_content = {
        "mt5": {
            "server": "test_server",
            "login": "test_login",
            "password": "test_password",
            "mt5_path": "test_path",
        },
        "symbols": ["EURUSD", "USDJPY"],
        "timeframe": "H4",
        "interval": 300,
        "risk": {"risk_per_trade": 0.01, "max_daily_loss": 0.05},
        "strategy": {
            "type": "turtle",
            "entry_period": 20,
            "exit_period": 10,
            "atr_period": 14,
            "vol_filter": True,
            "vol_lookback": 100,
            "vol_threshold": 1.2,
        },
    }
    config_path = tmp_path / "settings.json"
    with open(config_path, "w") as file:
        import json
        json.dump(config_content, file)
    return str(config_path)


def test_initialization_with_config(temp_config_file):
    trader = SophiaTrader(config_path=temp_config_file)
    assert trader.config_path == temp_config_file
    assert isinstance(trader.config, dict)
    assert "mt5" in trader.config
    assert "symbols" in trader.config
    assert "risk" in trader.config


def test_initialization_without_config(tmp_path):
    trader = SophiaTrader(config_path=None)
    assert isinstance(trader.config, dict)
    assert "mt5" in trader.config
    assert "symbols" in trader.config
    assert "risk" in trader.config
    assert os.path.exists(trader.config_path)


def test_initialize_components_successful(temp_config_file):
    trader = SophiaTrader(config_path=temp_config_file)
    result = trader.initialize_components()
    assert result is True
    assert trader.connector is not None
    assert trader.risk_manager is not None
    assert trader.strategy is not None


def test_initialize_components_failures(monkeypatch):
    trader = SophiaTrader()

    def mock_connector_fail(*args, **kwargs):
        return None

    monkeypatch.setattr("src.core.connector.MT5Connector.connect",
                        mock_connector_fail)
    result = trader.initialize_components()
    assert result is False


def test_run_trading_loop(monkeypatch, temp_config_file):
    trader = SophiaTrader(config_path=temp_config_file)

    def mock_initialize_components(*args, **kwargs):
        return True

    def mock_process_symbol(*args, **kwargs):
        pass

    monkeypatch.setattr(trader, "initialize_components",
                        mock_initialize_components)
    monkeypatch.setattr(trader, "_process_symbol", mock_process_symbol)
    trader.config["symbols"] = ["EURUSD", "USDJPY"]
    trader.config["interval"] = 1  # Reduce interval for quick test

    import threading

    def run_trading_loop():
        trader.run()

    def stop_trading_loop():
        trader.running = False

    thread = threading.Thread(target=run_trading_loop)
    thread.start()
    stop_trading_loop()
    thread.join()

    assert not trader.running
