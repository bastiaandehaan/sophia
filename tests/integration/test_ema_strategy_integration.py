from unittest.mock import MagicMock
import pandas as pd
import pytest
import sys
import importlib

# Mock MetaTrader5 voordat we MT5Connector importeren
sys.modules['MetaTrader5'] = MagicMock()

# Forceer reload van de module om caching te vermijden
if 'src.strategies.ema_strategy' in sys.modules:
    del sys.modules['src.strategies.ema_strategy']
importlib.import_module('src.strategies.ema_strategy')
from src.strategies.ema_strategy import EMAStrategy
from src.core.connector import MT5Connector
from src.core.risk import RiskManager

@pytest.mark.integration
def test_ema_strategy_full_workflow():
    # Arrange
    connector = MT5Connector(
        {"mt5_path": "test_path", "login": 123, "password": "test", "server": "test"}
    )
    connector.mt5 = MagicMock()
    connector.mt5.initialize.return_value = True

    # Simuleer een recente EMA en MACD crossover
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=100, freq="4H"),
        "open": [1.2] * 100,
        "high": [1.21] * 99 + [1.35],  # Scherpe stijging alleen op de laatste bar
        "low": [1.19] * 100,
        "close": [1.2] * 99 + [1.35]   # Stabiel tot de laatste bar, dan scherpe stijging
    })

    # Belangrijk: vervang de hele methode
    connector.get_historical_data = MagicMock(return_value=historical_data)

    # Mock account info en order plaatsing
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})
    connector.place_order = MagicMock(return_value={"success": True, "order_id": "12345"})

    risk_manager = RiskManager({"risk_per_trade": 0.01, "max_daily_loss": 0.05})
    risk_manager.calculate_position_size = MagicMock(return_value=0.1)

    strategy = EMAStrategy(
        connector,
        risk_manager,
        {"fast_ema": 9, "slow_ema": 21, "signal_ema": 5}
    )
    strategy.logger = MagicMock()
    strategy.logger.debug = print
    strategy.logger.info = print
    strategy.testing = True  # Vermijd tijdscontroles

    # Debug: Bereken indicatoren handmatig
    df = strategy.calculate_indicators(historical_data)
    indicators = {
        "current_price": df["close"].iloc[-1],
        "fast_ema": df["fast_ema"].iloc[-1],
        "slow_ema": df["slow_ema"].iloc[-1],
        "macd": df["macd"].iloc[-1],
        "signal": df["signal"].iloc[-1],
        "macd_hist": df["macd_hist"].iloc[-1],
        "prev_macd_hist": df["macd_hist"].iloc[-2],
        "rsi": df["rsi"].iloc[-1],
        "momentum": df["momentum"].iloc[-1],
        "bollinger_mid": df["bollinger_mid"].iloc[-1]
    }
    for key, value in indicators.items():
        print(f"DEBUG: {key}: {value}")

    # Act
    signal_result = strategy.check_signals("EURUSD", data=historical_data)

    # Assert signal
    assert signal_result["signal"] in ["BUY", "SELL"], "EMA crossover zou een signaal moeten genereren"

    # Execute signal
    if signal_result["signal"] in ["BUY", "SELL"]:
        execution_result = strategy.execute_signal(signal_result)
        assert execution_result["success"], "Signaaluitvoering zou moeten slagen"
    else:
        execution_result = None

    # Debug
    print("DEBUG: Signal result:", signal_result)
    print("DEBUG: Execution result:", execution_result)