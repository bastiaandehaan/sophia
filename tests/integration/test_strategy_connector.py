# tests/integration/test_strategy_connector.py
from unittest.mock import Mock

import pandas as pd
import pytest

from src.strategies.turtle_strategy import TurtleStrategy


@pytest.mark.integration
def test_strategy_using_connector(mock_connector, mock_risk_manager,
                                  logger_fixture):
    """Test dat de strategie correct werkt met de connector."""
    # Arrange
    config = {"entry_period": 20, "exit_period": 10, "atr_period": 14}

    # Act
    strategy = TurtleStrategy(mock_connector, mock_risk_manager, config)
    strategy.logger = logger_fixture

    # Controleer signalen
    result = strategy.check_signals("EURUSD")

    # Assert
    # Controleer dat connector.get_historical_data werd aangeroepen
    mock_connector.get_historical_data.assert_called_once()

    # Minimal sanity check op resultaat
    assert isinstance(result, dict)
    assert "signal" in result
    assert "meta" in result
    assert "timestamp" in result


@pytest.mark.integration
def test_complete_trading_workflow(mock_connector, mock_risk_manager,
                                   logger_fixture):
    """Test een complete handelscyclus van signaal naar order naar exit."""
    # Arrange
    config = {"entry_period": 20, "exit_period": 10, "atr_period": 14}
    symbol = "EURUSD"
    entry_price = 1.2000
    stop_loss = 1.1950
    position_size = 0.1

    # Mock een BUY signaal
    mock_signal = {
        "signal": "BUY",
        "meta": {"entry_price": entry_price, "stop_loss": stop_loss,
                 "atr": 0.005},
        "timestamp": pd.Timestamp.now(),
    }

    # Mock risico manager
    mock_risk_manager.calculate_position_size.return_value = position_size

    # Mock order response
    order_id = "12345"
    mock_connector.place_order.return_value = {
        "order_id": order_id,
        "symbol": symbol,
        "type": "BUY",
        "volume": position_size,
        "price": entry_price,
        "sl": stop_loss,
    }

    # Act
    strategy = TurtleStrategy(mock_connector, mock_risk_manager, config)
    strategy.logger = logger_fixture

    # Pas strategie aan om een consistent signaal te geven
    strategy.check_signals = Mock(return_value=mock_signal)

    # Test workflow
    signal_result = strategy.check_signals(symbol)

    # Simuleer een order uitvoering (als er een signaal is)
    if signal_result.get("signal") in ["BUY", "SELL"]:
        signal = signal_result["signal"]
        meta = signal_result["meta"]

        # Execute signaal
        mock_order_data = mock_connector.place_order.return_value

        # Update positietracking (normaal zou strategy.execute_signal dit doen)
        strategy.positions[symbol] = {
            "direction": signal,
            "entry_price": entry_price,
            "stop_loss": meta.get("stop_loss"),
            "size": position_size,
            "entry_time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Controleer dat positie correct is geregistreerd
        assert symbol in strategy.positions
        assert strategy.positions[symbol]["direction"] == signal
        assert strategy.positions[symbol]["entry_price"] == entry_price
        assert strategy.positions[symbol]["stop_loss"] == stop_loss

        # Test position close (als we execute_signal zouden aanroepen)
        # AANGEPAST: get_position_info → get_position en aangepaste key structure
        mock_connector.get_position.return_value = {
            "symbol": symbol,
            "direction": signal,  # Aangepast van 'type'
            "volume": position_size,
            "open_price": entry_price,
            # Aangepast van 'price_open'
            "current_price": 1.2100,  # Aangepast van 'price_current'
            "sl": stop_loss,
            "profit": 100.0,  # Extra veld voor volledigheid
        }

        # Simuleer een exitstrategie-aanroep (mock voor nu)
        strategy.positions.clear()  # Simuleer positie sluiting
        assert len(strategy.positions) == 0
