from datetime import datetime, timedelta

import backtrader as bt
import numpy as np
import pandas as pd


class BacktraderTestHelper:
    """Helper class voor het testen van BackTrader strategieën."""

    @staticmethod
    def create_test_strategy(strategy_class, strategy_params=None):
        """
        Creëer een testbare BackTrader strategie met een minimale omgeving.
        """
        # Standaard parameters als niet meegegeven
        if strategy_params is None:
            strategy_params = {}

        # Maak een Cerebro instantie
        cerebro = bt.Cerebro()
        cerebro.broker.set_cash(10000)

        # Bereken de maximale periode die nodig is voor indicators
        max_period = 50  # Standaard waarde
        for key, value in strategy_params.items():
            if 'period' in key and isinstance(value, int):
                max_period = max(max_period, value * 3)  # 3x voor veiligheid

        # Maak meer data om periodefouten te voorkomen
        data_length = max(200, max_period * 2)

        # Genereer data met een duidelijke trend en wat volatiliteit
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=data_length),
            periods=data_length)

        # Trend met wat randomness voor realistischere data
        base = np.linspace(100, 120, data_length)
        noise = np.random.normal(0, 1, data_length)

        # IMPORTANT FIX: Set the dates as the index of the DataFrame
        df = pd.DataFrame({
            'open': base + noise,
            'high': base + 2 + np.random.rand(data_length) * 2,
            'low': base - 2 - np.random.rand(data_length) * 2,
            'close': base + np.random.normal(0, 0.5, data_length),
            'volume': np.random.randint(1000, 10000, data_length),
            'openinterest': 0,
        }, index=dates)  # Set the dates as the index!

        # Zorg ervoor dat high altijd > low is
        df['high'] = np.maximum(df['high'],
                                np.maximum(df['open'], df['close']) + 0.5)
        df['low'] = np.minimum(df['low'],
                               np.minimum(df['open'], df['close']) - 0.5)

        # Voeg data toe aan Cerebro
        data_feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data_feed)

        # Voeg de strategie toe met de parameters
        cerebro.addstrategy(strategy_class, **strategy_params)

        # We gebruiken deze methode om de strategie te initialiseren zonder de volledige run
        strats = cerebro.run(stdstats=False)

        # Return de geïnitialiseerde strategie (eerste is de enige strategie)
        return strats[0]