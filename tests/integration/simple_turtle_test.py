# simple_turtle_test.py - Verbeterde debug-versie
from unittest.mock import MagicMock

import pandas as pd
import numpy as np

from src.strategies.turtle_strategy import TurtleStrategy


def run_simple_test():
    """Eenvoudige test die direct een TurtleStrategy test met vereenvoudigde data."""
    # Maak een nóg duidelijkere breakout dataset met steile prijsstijging
    data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=100, freq="h"),
        "open": [1.0] * 100,
        "high": [1.1] * 70 + [1.2] * 20 + [1.6] * 10,  # Gefaseerde stijging
        "low": [0.9] * 100,
        "close": [1.0] * 70 + [1.15] * 20 + [1.5] * 10  # Gefaseerde stijging
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
        "entry_period": 20,  # We kijken 20 periodes terug voor entry niveau
        "exit_period": 10,  # 10 periodes voor exit niveau
        "atr_period": 14,  # ATR berekenen over 14 periodes
        "vol_filter": False,  # Geen volatiliteitsfilter
        "trend_filter": False,  # Geen trendfilter
    })

    # Zet testing mode aan
    strategy.testing = True
    strategy.logger = MagicMock()

    # DEBUGGING: Bereken indicators direct
    print("\n" + "=" * 50)
    print("STAP 1: CALCULATE INDICATORS HANDMATIG")
    df_with_indicators = strategy.calculate_indicators(data)

    # Print de laatste 10 rijen met alle indicators voor analyse
    print("\nIndicator data (laatste 10 rijen):")
    columns_to_show = ['close', 'entry_high', 'entry_low']
    print(df_with_indicators[columns_to_show].tail(10))

    # DEBUGGING: Analyseer de entry_high waarden specifiek
    if 'entry_high' in df_with_indicators.columns:
        print("\nEntry high waarden (laatste 30 rijen):")
        for i in range(max(0, len(df_with_indicators) - 30),
                       len(df_with_indicators)):
            print(f"Rij {i}: {df_with_indicators['entry_high'].iloc[i]}")

    # DEBUGGING: Specificeer de waarden die we zouden moeten gebruiken voor breakout detectie
    last_price = df_with_indicators['close'].iloc[-1]
    if len(df_with_indicators) > 2:
        prev_entry_high = df_with_indicators['entry_high'].iloc[-2]
        print(
            f"\nBreakout check zou moeten zijn: {last_price} > {prev_entry_high}")
        print(f"Is breakout? {last_price > prev_entry_high}")

    # Check signalen
    print("\n" + "=" * 50)
    print("STAP 2: CHECK_SIGNALS AANROEPEN")
    signal_result = strategy.check_signals("EURUSD", data=data)

    # Toon resultaat
    print("\n" + "=" * 50)
    print(f"SIGNAL RESULT: {signal_result}")
    print("=" * 50)

    # DEBUGGING: Forceer een handmatige test met voorgedefinieerde waarden
    print("\nSTAP 3: HANDMATIGE TEST MET VOORGEDEFINIEERDE WAARDEN")
    test_indicators = {
        "current_price": 1.5,
        "prev_entry_high": 1.2,
        "prev_entry_low": 0.9,
        "prev_exit_high": 1.2,
        "prev_exit_low": 0.9,
        "atr": 0.1,
        "vol_filter": True,
        "trend_up": True,
        "trend_down": True
    }
    print("Test indicators:", test_indicators)
    manual_result = strategy._generate_signal("EURUSD", data, test_indicators,
                                              None)
    print(f"Handmatig resultaat: {manual_result}")

    return signal_result


if __name__ == "__main__":
    result = run_simple_test()

    # Conclusie
    if result and result.get("signal") == "BUY":
        print("\n✅ TEST GESLAAGD: BUY signaal gegenereerd zoals verwacht")
    else:
        print("\n❌ TEST GEFAALD: Geen BUY signaal gegenereerd")
        print("Controleer bovenstaande debug-informatie voor details.")