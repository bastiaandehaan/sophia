# tests/integration/test_turtle_strategy_integration.py
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.connector import MT5Connector
from src.core.risk import RiskManager
from src.strategies.turtle_strategy import TurtleStrategy


@pytest.mark.integration
def test_turtle_strategy_full_workflow():
    # Arrange
    connector = MT5Connector(
        {"mt5_path": "test_path", "login": 123, "password": "test",
         "server": "test"})
    connector.mt5 = MagicMock()
    connector.mt5.initialize.return_value = True
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=30, freq="4H"),
        "open": [1.2] * 30,
        "high": [1.21] * 20 + [1.25] * 10,  # Breakout
        "low": [1.19] * 30,
        "close": [1.2] * 20 + [1.24] * 10
    })
    connector.get_historical_data.return_value = historical_data

    risk_manager = RiskManager({"risk_per_trade": 0.01, "max_daily_loss": 0.05})
    risk_manager.calculate_position_size.return_value = 0.1

    strategy = TurtleStrategy(connector, risk_manager,
                              {"entry_period": 20, "exit_period": 10,
                               "atr_period": 14})
    strategy.logger = MagicMock()

    # Act
    signal_result = strategy.check_signals("EURUSD")
    if signal_result["signal"] in ["BUY", "SELL"]:
        execution_result = strategy.execute_signal(signal_result)

    # Assert
    assert signal_result["signal"] == "BUY"
    assert execution_result["success"], "Signaaluitvoering zou moeten slagen"