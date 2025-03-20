# src/strategy.py
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, Any, Optional


class TurtleStrategy:
    """Eenvoudige implementatie van de Turtle Trading strategie"""

    def __init__(self, connector, risk_manager, config):
        """
        Initialiseer de Turtle Trading strategie.

        Args:
            connector: Connector voor marktdata en order uitvoering
            risk_manager: Risk manager voor positiegrootte berekening
            config: Configuratie dictionary met strategie parameters
        """
        self.connector = connector
        self.risk_manager = risk_manager
        self.config = config
        self.logger = logging.getLogger("sophia")

        # Strategie parameters
        self.entry_period = config.get("entry_period", 20)
        self.exit_period = config.get("exit_period", 10)
        self.atr_period = config.get("atr_period", 14)

        # Positie tracking
        self.positions = {}

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Bereken indicators voor de Turtle strategie.

        Args:
            data: DataFrame met historische prijsdata

        Returns:
            DataFrame met toegevoegde indicators
        """
        # Maak kopie om originele data niet te wijzigen
        df = data.copy()

        # Donchian Channel voor entry
        df['entry_high'] = df['high'].rolling(window=self.entry_period).max()
        df['entry_low'] = df['low'].rolling(window=self.entry_period).min()

        # Donchian Channel voor exit
        df['exit_high'] = df['high'].rolling(window=self.exit_period).max()
        df['exit_low'] = df['low'].rolling(window=self.exit_period).min()

        # ATR berekening
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(window=self.atr_period).mean()

        return df

    def check_signals(self, symbol: str, data: Optional[pd.DataFrame] = None) -> Dict[
        str, Any]:
        """
        Controleer op handelssignalen.

        Args:
            symbol: Handelssymbool om te analyseren
            data: Optionele DataFrame met historische data (voor tests)

        Returns:
            Dictionary met signaal informatie
        """
        if data is None:
            # Haal data op als deze niet is meegegeven
            data = self.connector.get_historical_data(symbol,
                self.config.get("timeframe", "D1"), self.entry_period + 50)

            if data is None:
                self.logger.error(f"Geen data beschikbaar voor {symbol}")
                return {"symbol": symbol, "signal": None, "meta": {},
                        "timestamp": datetime.now()}

        # Bereken indicators
        data = self.calculate_indicators(data)

        # Controleer of we een positie hebben
        position = self.positions.get(symbol)
        current_direction = position['direction'] if position else None

        # Verzamel indicators voor signaal generatie
        indicators = {"current_price": data['close'].iloc[-1],
            "previous_entry_high": data['entry_high'].iloc[-2],
            "previous_entry_low": data['entry_low'].iloc[-2],
            "previous_exit_high": data['exit_high'].iloc[-2],
            "previous_exit_low": data['exit_low'].iloc[-2],
            "current_atr": data['atr'].iloc[-1], "trend_up": True,  # Simplified for now
            "trend_down": True  # Simplified for now
        }

        # Genereer signaal
        return self._generate_signal(symbol, data, indicators, current_direction)

    def _generate_signal(self, symbol: str, data: pd.DataFrame,
                         indicators: Dict[str, Any],
                         current_direction: Optional[str]) -> Dict[str, Any]:
        """
        Genereer een handelssignaal op basis van de berekende indicators.

        Args:
            symbol: Handelssymbool
            data: DataFrame met historische data en indicators
            indicators: Dictionary met indicators voor signaal generatie
            current_direction: Huidige positierichting ('BUY', 'SELL' of None)

        Returns:
            Dictionary met signaal informatie
        """
        current_price = indicators["current_price"]
        prev_entry_high = indicators["previous_entry_high"]
        prev_entry_low = indicators["previous_entry_low"]
        prev_exit_high = indicators["previous_exit_high"]
        prev_exit_low = indicators["previous_exit_low"]
        current_atr = indicators["current_atr"]

        signal = None
        meta = {}

        # Entry logica - als we geen positie hebben
        if current_direction is None:
            # Long entry (breakout boven entry_high)
            if current_price > prev_entry_high and indicators.get("trend_up", True):
                signal = "BUY"
                entry_price = prev_entry_high
                stop_loss = entry_price - (2 * current_atr)
                meta = {"entry_price": entry_price, "stop_loss": stop_loss,
                    "reason": "long_entry_breakout", "atr": current_atr}

            # Short entry (breakout onder entry_low)
            elif current_price < prev_entry_low and indicators.get("trend_down", True):
                signal = "SELL"
                entry_price = prev_entry_low
                stop_loss = entry_price + (2 * current_atr)
                meta = {"entry_price": entry_price, "stop_loss": stop_loss,
                    "reason": "short_entry_breakout", "atr": current_atr}

        # Exit logica - voor bestaande posities
        elif current_direction == "BUY":
            # Exit long positie als prijs onder exit_low daalt
            if current_price < prev_exit_low:
                signal = "CLOSE_BUY"
                meta = {"reason": "long_exit_breakout"}

        elif current_direction == "SELL":
            # Exit short positie als prijs boven exit_high stijgt
            if current_price > prev_exit_high:
                signal = "CLOSE_SELL"
                meta = {"reason": "short_exit_breakout"}

        if signal:
            self.logger.info(f"Signaal voor {symbol}: {signal} - {meta.get('reason')}")

        return {"symbol": symbol, "signal": signal, "meta": meta,
            "timestamp": datetime.now()}

    def check_signals_with_data(self, symbol: str, data: pd.DataFrame) -> Dict[
        str, Any]:
        """
        Check voor signalen met voorbewerkte data (voor tests).

        Args:
            symbol: Handelssymbool
            data: DataFrame met historische data

        Returns:
            Dict met signaal informatie
        """
        # Bereken indicators als dat nog niet is gebeurd
        if "entry_high" not in data.columns:
            data = self.calculate_indicators(data)

        # Controleer of we een positie hebben
        position = self.positions.get(symbol)
        current_direction = position["direction"] if position else None

        # Huidige prijs
        current_price = data["close"].iloc[-1]

        # Generator signaal
        return self._generate_signal(symbol, data, {"current_price": current_price,
            "previous_entry_high": data["entry_high"].iloc[-2],
            "previous_entry_low": data["entry_low"].iloc[-2],
            "previous_exit_high": data["exit_high"].iloc[-2],
            "previous_exit_low": data["exit_low"].iloc[-2],
            "current_atr": data["atr"].iloc[-1],
            "trend_up": data["close"].iloc[-1] > data["close"].iloc[-20],
            "trend_down": data["close"].iloc[-1] < data["close"].iloc[-20]},
                                     current_direction)

    def get_name(self) -> str:
        """
        Geeft de naam van de strategie terug.

        Returns:
            Naam van de strategie
        """
        return "Turtle Trading Strategy"