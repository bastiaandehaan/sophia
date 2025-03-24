# turtle_debug_test.py - Testen van de TurtleStrategy met directe stapsgewijze observatie
import datetime
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from src.strategies.turtle_strategy import TurtleStrategy


def main():
    # Creëer een zeer duidelijke breakout dataset
    periods = 100
    data = pd.DataFrame({
        "time": pd.date_range(start="2023-01-01", periods=periods, freq="D"),
        "open": np.ones(periods) * 1.0,
        "high": np.ones(periods) * 1.1,  # Basis high is 1.1
        "low": np.ones(periods) * 0.9,
        "close": np.ones(periods) * 1.0,
    })

    # Maak de laatste 10 records een duidelijke breakout
    data.loc[90:, "high"] = 1.5  # Verhoog high van 1.1 naar 1.5
    data.loc[90:, "close"] = 1.4  # Verhoog close van 1.0 naar 1.4

    print(f"Dataset shape: {data.shape}")
    print("Data head:")
    print(data.head())
    print("Data tail (met breakout):")
    print(data.tail())

    # Creëer strategie met eenvoudige instellingen
    connector = MagicMock()
    risk_manager = MagicMock()
    strategy = TurtleStrategy(connector, risk_manager, {
        "entry_period": 20,
        "exit_period": 10,
        "atr_period": 14,
        "vol_filter": False,  # Voor eenvoud
        "trend_filter": False  # Voor eenvoud
    })
    strategy.logger = MagicMock()
    strategy.testing = True  # Vermijd tijdscontroles

    # STAP 1: Calculate_indicators - Handmatig aanroepen
    print("\n----- STAP 1: CALCULATE INDICATORS -----")
    df_with_indicators = strategy.calculate_indicators(data)

    # Controleer resultaten van indicators
    print("\nIndicator resultaten (laatste records):")
    important_cols = ['high', 'close', 'entry_high', 'entry_low']
    print(df_with_indicators[important_cols].tail())

    # Controleer op NaN waardes die problemen kunnen veroorzaken
    for col in ['entry_high', 'entry_low', 'exit_high', 'exit_low']:
        nan_count = df_with_indicators[col].isna().sum()
        print(f"NaN in {col}: {nan_count} records")

    # Controleer op breakout voorwaarde in de laatste rij
    last_idx = len(df_with_indicators) - 1
    current_price = df_with_indicators['close'].iloc[last_idx]
    prev_entry_high = df_with_indicators['entry_high'].iloc[last_idx - 1]

    print(f"\nBreakout check op laatste record:")
    print(f"Current price: {current_price}")
    print(f"Previous entry high: {prev_entry_high}")
    print(f"Breakout? {current_price > prev_entry_high}")

    # STAP 2: Controleer signaal generatie
    print("\n----- STAP 2: SIGNAAL GENERATIE -----")

    # Maak dictionary van indicators die we naar _generate_signal zouden doorgeven
    indicators = {
        "current_price": df_with_indicators['close'].iloc[last_idx],
        "prev_entry_high": df_with_indicators['entry_high'].iloc[last_idx - 1],
        "prev_entry_low": df_with_indicators['entry_low'].iloc[last_idx - 1],
        "prev_exit_high": df_with_indicators['exit_high'].iloc[last_idx - 1],
        "prev_exit_low": df_with_indicators['exit_low'].iloc[last_idx - 1],
        "atr": df_with_indicators['atr'].iloc[last_idx],
        "vol_filter": True,  # Force True omdat we vol_filter uit hebben gezet
        "trend_up": True,  # Force True omdat we trend_filter uit hebben gezet
        "trend_down": True
        # Force True voor short signalen (niet relevant voor onze test)
    }

    print("Indicators voor _generate_signal:")
    for k, v in indicators.items():
        print(f"  {k}: {v}")

    # Call _generate_signal direct
    signal = strategy._generate_signal("EURUSD", df_with_indicators, indicators,
                                       None)

    # Print result
    print(f"\nSignaal resultaat: {signal}")

    # STAP 3: Check_signals volledige functie
    print("\n----- STAP 3: CHECK_SIGNALS FUNCTIE -----")
    result = strategy.check_signals("EURUSD", data=data)
    print(f"check_signals resultaat: {result}")

    # Conclusie
    if signal['signal'] == "BUY":
        print("\n✅ _generate_signal produceert correct BUY signaal")
    else:
        print("\n❌ _generate_signal produceert GEEN BUY signaal")

    if result['signal'] == "BUY":
        print("\n✅ check_signals produceert correct BUY signaal")
    else:
        print("\n❌ check_signals produceert GEEN BUY signaal")

    # Oplossing suggestie
    print("\n----- MOGELIJKE FIXES -----")
    print(
        "Als er geen BUY signaal wordt gegenereerd, probeer de volgende aanpassingen in turtle_strategy.py:")
    print("1. Controleer entry_high berekening in calculate_indicators")
    print("2. Controleer breakout voorwaarde in _generate_signal")
    print(
        "3. Probeer handmatig deze indicatorwaarden toe te voegen aan _generate_signal: ")
    print("""
    indicators = {
        "current_price": 1.4,
        "prev_entry_high": 1.1,
        "prev_entry_low": 0.9,
        "prev_exit_high": 1.1,
        "prev_exit_low": 0.9,
        "atr": 0.1,
        "vol_filter": True,
        "trend_up": True,
        "trend_down": True
    }
    """)
    print("4. Fix het calculate_position_size.return_value attribuut in tests")


if __name__ == "__main__":
    main()