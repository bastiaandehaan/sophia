# tests/integration/test_turtle_strategy_integration.py
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.risk import RiskManager
from src.strategies.turtle_strategy import TurtleStrategy


@pytest.mark.integration
def test_turtle_strategy_full_workflow():
    # Arrange
    connector = MagicMock()

    # Maak een zeer duidelijke breakout dataset
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=100, freq="D"),
        "open": [1.0] * 100,
        "high": [1.1] * 90 + [1.5] * 10,  # Extreme breakout
        "low": [0.9] * 100,
        "close": [1.0] * 90 + [1.4] * 10  # Extreme stijging
    })

    # Mocks configureren
    connector.get_historical_data = MagicMock(return_value=historical_data)
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})
    connector.place_order = MagicMock(
        return_value={"success": True, "order_id": "12345"})

    # Gebruik patch om het probleem met risk_manager.calculate_position_size.return_value op te lossen
    with patch.object(RiskManager, 'calculate_position_size', return_value=0.1):
        risk_manager = RiskManager(
            {"risk_per_trade": 0.01, "max_daily_loss": 0.05})

        strategy = TurtleStrategy(connector, risk_manager, {
            "entry_period": 20,
            "exit_period": 10,
            "atr_period": 14,
            "vol_filter": False  # Uitschakelen voor test eenvoud
        })

        strategy.logger = MagicMock()
        strategy.testing = True  # Vermijd tijdscontroles

        # Act
        signal_result = strategy.check_signals("EURUSD")

        # Assert
        assert signal_result[
                   "signal"] == "BUY", "Moet een BUY signaal genereren"

        # Voer het signaal uit
        execution_result = strategy.execute_signal(signal_result)
        assert execution_result[
            "success"], "Signaaluitvoering zou moeten slagen"