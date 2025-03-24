import pandas as pd
from unittest.mock import MagicMock
import pytest
from your_module import EMAStrategy, RiskManager, \
    MT5Connector  # Vervang 'your_module' door de juiste module naam


@pytest.mark.integration
def test_ema_strategy_full_workflow():
    # Arrange
    connector = MT5Connector(
        {"mt5_path": "test_path", "login": 123, "password": "test",
         "server": "test"}
    )
    connector.mt5 = MagicMock()
    connector.mt5.initialize.return_value = True

    # Simuleer een EMA-crossover met dalende en stijgende close-prijzen
    historical_data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=50, freq="4H"),
        "open": [1.2] * 50,
        "high": [1.21] * 50,
        "low": [1.19] * 50,
        "close": [1.2] * 30 + [1.18] * 10 + [1.25] * 10  # Daling, dan stijging
    })

    # Mock de get_historical_data methode
    connector.get_historical_data = MagicMock(return_value=historical_data)
    connector.get_account_info = MagicMock(return_value={"balance": 10000.0})
    connector.place_order = MagicMock(
        return_value={"success": True, "order_id": "12345"})

    # Configureer RiskManager
    risk_manager = RiskManager({"risk_per_trade": 0.01, "max_daily_loss": 0.05})
    risk_manager.calculate_position_size = MagicMock(return_value=0.1)

    strategy = EMAStrategy(
        connector,
        risk_manager,
        {
            "fast_ema": 9,  # Snelle EMA
            "slow_ema": 21,  # Langzame EMA
            "signal_ema": 5  # Signaal EMA
        }
    )

    # Mock logger
    strategy.logger = MagicMock()

    # Act
    signal_result = strategy.check_signals("EURUSD")

    # Assert
    assert signal_result["signal"] in ["BUY",
                                       "SELL"], "EMA-crossover zou een signaal moeten genereren"
    # Optioneel: specificeer BUY als je zeker weet dat fast_ema > slow_ema na de stijging
    assert signal_result[
               "signal"] == "BUY", "Moet een BUY-signaal genereren na crossover"
