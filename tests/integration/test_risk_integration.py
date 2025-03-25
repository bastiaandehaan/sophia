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
def test_risk_with_strategy_and_connector():
    # Arrange
    connector = MagicMock()

    # Mock get_historical_data met voldoende data
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=230, freq="4H"),
        "open": [1.0] * 230,
        "high": [1.1] * 220 + [1.5] * 10,  # Breakout in de laatste 10 bars
        "low": [0.9] * 230,
        "close": [1.0] * 220 + [1.4] * 9 + [1.6]  # Extreme stijging
    })
    connector.get_historical_data = MagicMock(return_value=historical_data)
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})

    # Maak een risk manager, patch calculate_position_size
    risk_config = {"risk_per_trade": 0.01, "max_daily_loss": 0.05}
    with patch.object(RiskManager, 'calculate_position_size', return_value=0.1):
        risk_manager = RiskManager(risk_config)

        # Creëer strategie
        strategy_config = {
            "entry_period": 20,
            "exit_period": 10,
            "atr_period": 14,
            "vol_filter": False,
            "trend_filter": False  # Expliciet uitschakelen voor consistentie
        }
        strategy = TurtleStrategy(connector, risk_manager, strategy_config)
        strategy.logger = MagicMock()
        strategy.logger.debug = print  # Voor debug-uitvoer
        strategy.logger.info = print
        strategy.testing = True  # Vermijd tijdscontroles

        # Act
        result = strategy.check_signals("EURUSD", data=historical_data)

        # Assert
        assert result["signal"] == "BUY", "Moet een BUY-signaal genereren"

        # Optionele debug
        print("DEBUG: Signal result:", result)