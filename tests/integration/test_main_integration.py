from unittest.mock import MagicMock
import pandas as pd
import pytest
import sys
import importlib

# Mock MetaTrader5 voordat we MT5Connector importeren
sys.modules['MetaTrader5'] = MagicMock()

# Forceer reload van de module om caching te vermijden
if 'src.strategies.turtle_strategy' in sys.modules:
    del sys.modules['src.strategies.turtle_strategy']
importlib.import_module('src.strategies.turtle_strategy')
from src.strategies.turtle_strategy import TurtleStrategy
from src.core.connector import MT5Connector

@pytest.mark.integration
def test_connector_with_strategy():
    # Arrange
    config = {"mt5_path": "test_path", "login": 123, "password": "test", "server": "test"}
    connector = MT5Connector(config)

    # Mock MT5 interacties
    connector.mt5 = MagicMock()
    connector.mt5.initialize.return_value = True
    connector.mt5.login.return_value = True
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=230, freq="4H"),
        "open": [1.2] * 230,
        "high": [1.21] * 220 + [1.25] * 10,  # Breakout in de laatste 10 bars
        "low": [1.19] * 230,
        "close": [1.2] * 220 + [1.24] * 9 + [1.26]  # Extreme stijging
    })

    # Belangrijk: vervang de hele methode
    connector.get_historical_data = MagicMock(return_value=historical_data)

    mock_risk_manager = MagicMock()
    mock_risk_manager.calculate_position_size.return_value = 0.1
    strategy_config = {
        "entry_period": 20,
        "exit_period": 10,
        "atr_period": 14,
        "vol_filter": False,  # Expliciet uitschakelen
        "trend_filter": False  # Expliciet uitschakelen voor consistentie
    }
    strategy = TurtleStrategy(connector, mock_risk_manager, strategy_config)

    # Mock logger voor debugging
    strategy.logger = MagicMock()
    strategy.logger.debug = print
    strategy.logger.info = print
    strategy.testing = True  # Vermijd tijdscontroles

    # Act
    result = strategy.check_signals("EURUSD", data=historical_data)

    # Assert
    assert "signal" in result
    assert result["signal"] == "BUY", "Verwacht een BUY-signaal door breakout"

    # Optionele debug
    print("DEBUG: Signal result:", result)