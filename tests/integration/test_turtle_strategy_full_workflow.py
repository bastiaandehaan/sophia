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
    connector = MagicMock()
    # Maak historische data met voldoende lengte (minstens 230 bars)
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=230, freq="D"),
        "open": [1.0] * 230,
        "high": [1.1] * 220 + [1.5] * 10,  # Breakout in de laatste 10 bars
        "low": [0.9] * 230,
        "close": [1.0] * 220 + [1.4] * 9 + [1.6]  # Breakout bij 1.6
    })
    connector.get_historical_data = MagicMock(return_value=historical_data)
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})
    connector.place_order = MagicMock(return_value={"success": True, "order_id": "12345"})
    with patch.object(RiskManager, 'calculate_position_size', return_value=0.1):
        risk_manager = RiskManager({"risk_per_trade": 0.01, "max_daily_loss": 0.05})
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
        strategy.logger = MagicMock()
        strategy.logger.debug = print
        strategy.logger.info = print
        strategy.testing = True
        print("DEBUG: Strategy version:", getattr(strategy, 'VERSION', 'Unknown'))
        data = strategy.calculate_indicators(historical_data)
        print("Laatste entry_high:", data["entry_high"].iloc[-1])
        print("Laatste close:", data["close"].iloc[-1])
        print("Gebruikte TurtleStrategy module:", TurtleStrategy.__module__)
        print("Bestandspad:", sys.modules['src.strategies.turtle_strategy'].__file__)
        # Geef data expliciet mee aan check_signals
        signal_result = strategy.check_signals("EURUSD", data=historical_data)
        print("Signaal resultaat:", signal_result)
        assert signal_result["signal"] == "BUY", "Moet een BUY-signaal genereren bij breakout"