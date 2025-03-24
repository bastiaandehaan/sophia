# tests/integration/test_ema_strategy_integration.py
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.connector import MT5Connector
from src.core.risk import RiskManager
from src.strategies.ema_strategy import EMAStrategy


@pytest.mark.integration
def test_ema_strategy_full_workflow():
    # Arrange
    connector = MT5Connector(
        {"mt5_path": "test_path", "login": 123, "password": "test",
         "server": "test"})
    connector.mt5 = MagicMock()
    connector.mt5.initialize.return_value = True
    # Simuleer EMA crossover
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=30, freq="4H"),
        "open": [1.2] * 30,
        "high": [1.21] * 30,
        "low": [1.19] * 30,
        "close": [1.2] * 20 + [1.25] * 10  # Snelle EMA kruist langzame
    })
    connector.get_historical_data.return_value = historical_data

    risk_manager = RiskManager({"risk_per_trade": 0.01, "max_daily_loss": 0.05})
    risk_manager.calculate_position_size.return_value = 0.1

    strategy = EMAStrategy(connector, risk_manager,
                           {"fast_ema": 9, "slow_ema": 21, "signal_ema": 5})
    strategy.logger = MagicMock()

    # Act
    signal_result = strategy.check_signals("EURUSD")
    if signal_result["signal"] in ["BUY", "SELL"]:
        execution_result = strategy.execute_signal(signal_result)

    # Assert
    assert signal_result["signal"] in ["BUY",
                                       "SELL"], "EMA crossover zou een signaal moeten genereren"
    assert execution_result["success"], "Signaaluitvoering zou moeten slagen"