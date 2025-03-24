# tests/integration/test_connector_integration.py
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.connector import MT5Connector
from src.strategies.turtle_strategy import TurtleStrategy


@pytest.mark.integration
def test_connector_with_strategy():
    # Arrange
    config = {"mt5_path": "test_path", "login": 123, "password": "test",
              "server": "test"}
    connector = MT5Connector(config)

    # Mock MT5 interacties
    connector.mt5 = MagicMock()
    connector.mt5.initialize.return_value = True
    connector.mt5.login.return_value = True
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=50, freq="4H"),
        "open": [1.2] * 50,
        "high": [1.21] * 40 + [1.25] * 10,  # Breakout
        "low": [1.19] * 50,
        "close": [1.2] * 40 + [1.24] * 10
    })

    # Belangrijk: vervang de hele methode
    connector.get_historical_data = MagicMock(return_value=historical_data)

    mock_risk_manager = MagicMock()
    mock_risk_manager.calculate_position_size.return_value = 0.1
    strategy_config = {"entry_period": 20, "exit_period": 10, "atr_period": 14}
    strategy = TurtleStrategy(connector, mock_risk_manager, strategy_config)

    # Act
    result = strategy.check_signals("EURUSD")

    # Assert
    assert "signal" in result
    assert result["signal"] == "BUY", "Verwacht een BUY-signaal door breakout"