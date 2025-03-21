# tests/unit/test_strategy.py
import pytest
import pandas as pd
import numpy as np
from src.strategy import TurtleStrategy


@pytest.fixture
def turtle_strategy(mock_connector, mock_risk_manager, logger_fixture):
    """Creëer een TurtleStrategy instantie voor tests."""
    config = {"entry_period": 20, "exit_period": 10, "atr_period": 14}
    strategy = TurtleStrategy(mock_connector, mock_risk_manager, config)
    strategy.logger = logger_fixture
    return strategy


def test_turtle_strategy_init(turtle_strategy):
    """Test TurtleStrategy initialisatie."""
    assert turtle_strategy.entry_period == 20
    assert turtle_strategy.exit_period == 10
    assert turtle_strategy.atr_period == 14
    assert isinstance(turtle_strategy.positions, dict)


def test_calculate_indicators(turtle_strategy, sample_ohlc_data):
    """Test het berekenen van indicators."""
    result = turtle_strategy.calculate_indicators(sample_ohlc_data)

    # Controleer of verwachte kolommen aanwezig zijn
    assert "entry_high" in result.columns
    assert "entry_low" in result.columns
    assert "exit_high" in result.columns
    assert "exit_low" in result.columns
    assert "atr" in result.columns

    # Controleer berekeningen
    assert result["entry_high"].iloc[25] >= max(sample_ohlc_data["high"].iloc[6:25])
    assert result["exit_high"].iloc[25] >= max(sample_ohlc_data["high"].iloc[16:25])

    # ATR moet positief zijn
    assert (result["atr"].iloc[20:] > 0).all()

    # NaN waarden aan begin vanwege het rolling window
    # Aangepast: controleer vanaf entry_period (20) in plaats van index 10
    assert result["entry_high"].iloc[turtle_strategy.entry_period:].notna().all()


def test_check_signals_buy(turtle_strategy, mock_connector, sample_ohlc_data):
    """Test signaaldetectie voor long entry."""
    # Voeg een duidelijk buy signaal toe (prijs boven entry high)
    modified_data = sample_ohlc_data.copy()

    # Bereken indicators
    data_with_indicators = turtle_strategy.calculate_indicators(modified_data)

    # Mock de connector om de gemodificeerde data te gebruiken
    mock_connector.get_historical_data.return_value = data_with_indicators

    # Zorg dat laatste prijs boven entry high ligt
    entry_high = data_with_indicators["entry_high"].iloc[-2]
    data_with_indicators.loc[
        data_with_indicators.index[-1], "close"] = entry_high * 1.01

    # Check voor signalen
    result = turtle_strategy.check_signals("EURUSD", data_with_indicators)

    # Controleer resultaat
    assert result["signal"] == "BUY"
    assert "entry_price" in result["meta"]
    assert "stop_loss" in result["meta"]
    assert result["meta"]["reason"] == "long_entry_breakout"


def test_check_signals_sell(turtle_strategy, mock_connector, sample_ohlc_data):
    """Test signaaldetectie voor short entry."""
    # Voeg een duidelijk sell signaal toe (prijs onder entry low)
    modified_data = sample_ohlc_data.copy()

    # Bereken indicators
    data_with_indicators = turtle_strategy.calculate_indicators(modified_data)

    # Zorg dat laatste prijs onder entry low ligt
    entry_low = data_with_indicators["entry_low"].iloc[-2]
    data_with_indicators.loc[data_with_indicators.index[-1], "close"] = entry_low * 0.99

    # Mock de connector om de gemodificeerde data te gebruiken
    mock_connector.get_historical_data.return_value = data_with_indicators

    # Check voor signalen
    result = turtle_strategy.check_signals("EURUSD", data_with_indicators)

    # Controleer resultaat
    assert result["signal"] == "SELL"
    assert "entry_price" in result["meta"]
    assert "stop_loss" in result["meta"]
    assert result["meta"]["reason"] == "short_entry_breakout"


def test_check_signals_no_signal(turtle_strategy, mock_connector, sample_ohlc_data):
    """Test detectie van geen signaal."""
    # Gebruik standaard data zonder speciale situatie
    data_with_indicators = turtle_strategy.calculate_indicators(sample_ohlc_data)

    # Mock de connector
    mock_connector.get_historical_data.return_value = data_with_indicators

    # Plaats de prijs in het midden van de range (geen signaal)
    entry_high = data_with_indicators["entry_high"].iloc[-2]
    entry_low = data_with_indicators["entry_low"].iloc[-2]
    mid_price = (entry_high + entry_low) / 2
    data_with_indicators.loc[data_with_indicators.index[-1], "close"] = mid_price

    # Check voor signalen
    result = turtle_strategy.check_signals("EURUSD", data_with_indicators)

    # Controleer resultaat
    assert result["signal"] is None


def test_check_signals_exit_long(turtle_strategy, mock_connector, sample_ohlc_data):
    """Test signaaldetectie voor long exit."""
    # Bereken indicators
    data_with_indicators = turtle_strategy.calculate_indicators(sample_ohlc_data)

    # Mock de connector
    mock_connector.get_historical_data.return_value = data_with_indicators

    # Simuleer bestaande long positie
    turtle_strategy.positions["EURUSD"] = {"direction": "BUY", "entry_price": 1.2000,
        "stop_loss": 1.1900, "size": 0.1, "entry_time": pd.Timestamp.now()}

    # Zet prijs onder exit low voor exit signaal
    exit_low = data_with_indicators["exit_low"].iloc[-2]
    data_with_indicators.loc[data_with_indicators.index[-1], "close"] = exit_low * 0.99

    # Check voor signalen
    result = turtle_strategy.check_signals("EURUSD", data_with_indicators)

    # Controleer resultaat
    assert result["signal"] == "CLOSE_BUY"
    assert result["meta"]["reason"] == "long_exit_breakout"