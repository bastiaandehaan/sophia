# simple_turtle_test.py
from unittest.mock import MagicMock

import pandas as pd
import numpy as np

from src.strategies.turtle_strategy import TurtleStrategy


def run_simple_test():
    """Eenvoudige test die direct een TurtleStrategy test met vereenvoudigde data."""
    # Maak een duidelijke breakout dataset
    data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=100, freq="4H"),
        "open": np.ones(100) * 1.0,
        "high": np.concatenate([np.ones(90) * 1.1, np.ones(10) * 1.5]),
        # Heel duidelijke breakout
        "low": np.ones(100) * 0.9,
        "close": np.concatenate([np.ones(90) * 1.0, np.ones(10) * 1.4])
        # Sterke stijging
    })

    # Print dataset info
    print(f"Dataset shape: {data.shape}")
    print("Eerste 5 rijen:")
    print(data.head())
    print("Laatste 5 rijen:")
    print(data.tail())

    # Maak mocks
    connector = MagicMock()
    connector.get_historical_data.return_value = data

    risk_manager = MagicMock()
    risk_manager.calculate_position_size.return_value = 0.1

    # Maak strategie met eenvoudige parameters en zet filters uit
    strategy = TurtleStrategy(connector, risk_manager, {
        "entry_period": 5,  # Korter voor duidelijke signalen
        "exit_period": 3,  # Korter voor duidelijke signalen
        "atr_period": 5,  # Korter voor snellere ATR berekening
        "vol_filter": False,  # Geen volatiliteitsfilter
        "trend_filter": False,  # Geen trendfilter
    })

    # Zet testing mode aan
    strategy.testing = True
    strategy.logger = MagicMock()

    # Check signalen
    signal_result = strategy.check_signals("EURUSD", data=data)

    # Toon resultaat
    print("\n" + "=" * 50)
    print(f"SIGNAL RESULT: {signal_result}")
    print("=" * 50)

    # Return voor eventuele verdere verwerking
    return signal_result


if __name__ == "__main__":
    result = run_simple_test()

    # Conclusie
    if result["signal"] == "BUY":
        print("\n✅ TEST GESLAAGD: BUY signaal gegenereerd zoals verwacht")
    else:
        print("\n❌ TEST GEFAALD: Geen BUY signaal gegenereerd")
        print("Controleer de debug output om te zien wat er mis ging.")