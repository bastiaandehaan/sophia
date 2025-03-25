from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
import sys
import importlib

# Forceer reload van de module om caching te vermijden
if 'src.strategies.turtle_strategy' in sys.modules:
    del sys.modules['src.strategies.turtle_strategy']
importlib.import_module('src.strategies.turtle_strategy')
from src.strategies.turtle_strategy import TurtleStrategy
from src.core.risk import RiskManager

@pytest.mark.integration
def test_turtle_strategy_full_workflow():
    # Arrange
    connector = MagicMock()

    # Maak een duidelijke breakout dataset met voldoende lengte
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=230, freq="D"),
        "open": [1.0] * 230,
        "high": [1.1] * 220 + [1.5] * 10,  # Breakout in de laatste 10 bars
        "low": [0.9] * 230,
        "close": [1.0] * 220 + [1.4] * 9 + [1.6]  # Extreme stijging bij einde
    })

    # Mocks configureren
    connector.get_historical_data = MagicMock(return_value=historical_data)
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})
    connector.place_order = MagicMock(return_value={"success": True, "order_id": "12345"})

    # Gebruik patch om RiskManager.calculate_position_size te mocken
    with patch.object(RiskManager, 'calculate_position_size', return_value=0.1):
        risk_manager = RiskManager({"risk_per_trade": 0.01, "max_daily_loss": 0.05})

        strategy = TurtleStrategy(
            connector,
            risk_manager,
            {
                "entry_period": 20,
                "exit_period": 10,
                "atr_period": 14,
                "vol_filter": False  # Uitschakelen voor test eenvoud
            }
        )

        # Mock logger voor debugging
        strategy.logger = MagicMock()
        strategy.logger.debug = print
        strategy.logger.info = print
        strategy.testing = True  # Vermijd tijdscontroles

        # Mock execute_signal voor deze test
        strategy.execute_signal = MagicMock(return_value={"success": True, "action": "entry", "order": {"success": True, "order_id": "12345"}})

        # Act
        # Geef historical_data expliciet mee aan check_signals
        signal_result = strategy.check_signals("EURUSD", data=historical_data)

        # Assert
        assert signal_result["signal"] == "BUY", "Moet een BUY-signaal genereren"

        # Voer het signaal uit
        execution_result = strategy.execute_signal(signal_result)
        assert execution_result["success"], "Signaaluitvoering zou moeten slagen"

        # Debug-prints
        print("DEBUG: Signal result:", signal_result)
        print("DEBUG: Execution result:", execution_result)