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
        "time": pd.date_range(start="2023-01-01", periods=50, freq="4H"),
        "open": [1.2] * 50,
        "high": [1.21] * 50,
        "low": [1.19] * 50,
        "close": [1.2] * 40 + [1.25] * 10  # Snelle EMA kruist langzame
    })

    # Belangrijk: vervang de hele methode
    connector.get_historical_data = MagicMock(return_value=historical_data)

    # Mock account info en order plaatsing
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})
    connector.place_order = MagicMock(
        return_value={"success": True, "order_id": "12345"})

    risk_manager = RiskManager({"risk_per_trade": 0.01, "max_daily_loss": 0.05})
    risk_manager.calculate_position_size = MagicMock(return_value=0.1)

    strategy = EMAStrategy(connector, risk_manager,
                           {"fast_ema": 9, "slow_ema": 21, "signal_ema": 5})
    strategy.logger = MagicMock()

    # Act
    signal_result = strategy.check_signals("EURUSD")

    # Assert signal
    assert signal_result["signal"] in ["BUY",
                                       "SELL"], "EMA crossover zou een signaal moeten genereren"

    # Execute signal
    if signal_result["signal"] in ["BUY", "SELL"]:
        execution_result = strategy.execute_signal(signal_result)
        assert execution_result[
            "success"], "Signaaluitvoering zou moeten slagen"