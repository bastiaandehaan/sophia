import pandas as pd
from unittest.mock import MagicMock, patch
import pytest
import sys
import importlib

# Forceer reload van de module
if 'src.strategies.turtle_strategy' in sys.modules:
    del sys.modules['src.strategies.turtle_strategy']
importlib.import_module('src.strategies.turtle_strategy')
from src.strategies.turtle_strategy import TurtleStrategy
from src.core.risk import RiskManager


@pytest.mark.integration
def test_turtle_strategy_full_workflow():
    # Arrange
    connector = MagicMock()

    # Maak historische data met een duidelijke breakout
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=100, freq="D"),
        "open": [1.0] * 100,
        "high": [1.1] * 90 + [1.5] * 10,
        "low": [0.9] * 100,
        "close": [1.0] * 90 + [1.4] * 9 + [1.6]
    })

    # Configureer mocks
    connector.get_historical_data = MagicMock(return_value=historical_data)
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})
    connector.place_order = MagicMock(
        return_value={"success": True, "order_id": "12345"})

    # Patch RiskManager.calculate_position_size
    with patch.object(RiskManager, 'calculate_position_size', return_value=0.1):
        risk_manager = RiskManager(
            {"risk_per_trade": 0.01, "max_daily_loss": 0.05})

        strategy = TurtleStrategy(
            connector,
            risk_manager,
            {
                "entry_period": 20,
                "exit_period": 10,
                "atr_period": 14,
                "vol_filter": False,
                "trend_filter": False
            }
        )

        # Mock logger met echte output voor debugging
        strategy.logger = MagicMock()
        strategy.logger.debug = print
        strategy.logger.info = print
        strategy.testing = True

        # Act
        data = strategy.calculate_indicators(historical_data)
        print("Laatste entry_high:", data["entry_high"].iloc[-1])
        print("Laatste close:", data["close"].iloc[-1])

        # Extra debug: print het pad van de gebruikte TurtleStrategy
        print("Gebruikte TurtleStrategy module:", TurtleStrategy.__module__)
        print("Bestandspad:",
              sys.modules['src.strategies.turtle_strategy'].__file__)

        signal_result = strategy.check_signals("EURUSD")
        print("Signaal resultaat:", signal_result)

        # Assert
        assert signal_result[
                   "signal"] == "BUY", "Moet een BUY-signaal genereren bij breakout"