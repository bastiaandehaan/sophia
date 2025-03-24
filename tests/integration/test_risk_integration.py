# tests/integration/test_risk_integration.py
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.connector import MT5Connector
from src.core.risk import RiskManager
from src.strategies.turtle_strategy import TurtleStrategy


@pytest.mark.integration
def test_risk_with_strategy_and_connector():
    # Arrange
    config = {"mt5_path": "test_path", "login": 123, "password": "test",
              "server": "test"}
    connector = MT5Connector(config)
    connector.mt5 = MagicMock()
    connector.mt5.initialize.return_value = True
    connector.mt5.account_info.return_value = MagicMock(balance=10000.0)
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})

    risk_config = {"risk_per_trade": 0.01, "max_daily_loss": 0.05}
    risk_manager = RiskManager(risk_config)

    strategy_config = {"entry_period": 20, "exit_period": 10, "atr_period": 14}
    strategy = TurtleStrategy(connector, risk_manager, strategy_config)

    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=30, freq="4H"),
        "open": [1.2] * 30,
        "high": [1.21] * 20 + [1.25] * 10,
        "low": [1.19] * 30,
        "close": [1.2] * 20 + [1.24] * 10
    })
    connector.get_historical_data = MagicMock(return_value=historical_data)

    # Act
    result = strategy.check_signals("EURUSD")
    if result["signal"] == "BUY":
        meta = result["meta"]
        position_size = risk_manager.calculate_position_size(
            account_balance=10000.0,
            entry_price=meta["entry_price"],
            stop_loss=meta["stop_loss"]
        )

    # Assert
    assert result["signal"] == "BUY"
    assert 0 < position_size <= 1.0, "Positiegrootte moet redelijk zijn"