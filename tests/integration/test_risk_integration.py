# tests/integration/test_risk_integration.py
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.connector import MT5Connector
from src.core.risk import RiskManager
from src.strategies.turtle_strategy import TurtleStrategy


@pytest.mark.integration
def test_risk_with_strategy_and_connector():
    # Arrange
    connector = MagicMock()

    # Mock get_historical_data
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=100, freq="4H"),
        "open": [1.0] * 100,
        "high": [1.1] * 90 + [1.5] * 10,  # Extreme breakout
        "low": [0.9] * 100,
        "close": [1.0] * 90 + [1.4] * 10  # Extreme stijging
    })
    connector.get_historical_data = MagicMock(return_value=historical_data)
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})

    # Maak een risk manager, maar PATCH de relevante methode
    risk_config = {"risk_per_trade": 0.01, "max_daily_loss": 0.05}

    # Optie 1: Gebruik patch op de klasse methode
    with patch.object(RiskManager, 'calculate_position_size', return_value=0.1):
        risk_manager = RiskManager(risk_config)

        # Creëer strategie
        strategy_config = {"entry_period": 20, "exit_period": 10,
                           "atr_period": 14, "vol_filter": False}
        strategy = TurtleStrategy(connector, risk_manager, strategy_config)
        strategy.logger = MagicMock()
        strategy.testing = True  # Vermijd tijdscontroles

        # Act
        result = strategy.check_signals("EURUSD")

        # Assert
        assert result["signal"] == "BUY"