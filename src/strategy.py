# src/strategy.py
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd


class TurtleStrategy:
    """
    Moderne implementatie van de Turtle Trading strategie.
    Inclusief volatiliteitsfilter voor betere prestaties in hedendaagse markten.
    """

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

        # Moderne toevoegingen - volatiliteitsfilter
        self.use_vol_filter = config.get("vol_filter", True)
        self.vol_lookback = config.get("vol_lookback", 100)
        self.vol_threshold = config.get("vol_threshold", 1.2)

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
        df["entry_high"] = df["high"].rolling(window=self.entry_period).max()
        df["entry_low"] = df["low"].rolling(window=self.entry_period).min()

        # Donchian Channel voor exit
        df["exit_high"] = df["high"].rolling(window=self.exit_period).max()
        df["exit_low"] = df["low"].rolling(window=self.exit_period).min()

        # ATR berekening
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df["atr"] = true_range.rolling(window=self.atr_period).mean()

        # Volatiliteitsfilter (moderne toevoeging)
        if self.use_vol_filter and len(df) > self.vol_lookback:
            # Bereken recente gemiddelde ATR
            recent_atr = df["atr"].iloc[-self.vol_lookback:].mean()
            # Huidige ATR
            current_atr = df["atr"].iloc[-1]
            # True als markt voldoende volatiel is
            df["vol_filter"] = current_atr > (recent_atr * self.vol_threshold)
        else:
            df["vol_filter"] = True  # Standaard aan wanneer niet genoeg data

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
                self.config.get("timeframe", "H4"), self.entry_period + 50)

            if data is None or len(data) < self.entry_period + 20:
                self.logger.error(f"Onvoldoende data beschikbaar voor {symbol}")
                return {"symbol": symbol, "signal": None, "meta": {},
                    "timestamp": datetime.now(), }

        # Bereken indicators
        data = self.calculate_indicators(data)

        # Controleer of we een positie hebben
        position = self.positions.get(symbol)
        current_direction = position["direction"] if position else None

        # Verzamel indicators voor signaal generatie
        indicators = {"current_price": data["close"].iloc[-1],
            "previous_entry_high": data["entry_high"].iloc[-2],
            "previous_entry_low": data["entry_low"].iloc[-2],
            "previous_exit_high": data["exit_high"].iloc[-2],
            "previous_exit_low": data["exit_low"].iloc[-2],
            "current_atr": data["atr"].iloc[-1], "vol_filter": (
                data["vol_filter"].iloc[-1] if "vol_filter" in data.columns else True),
            "trend_up": data["close"].iloc[-1] > data["close"].iloc[-20],
            # Eenvoudige trendfilter
            "trend_down": data["close"].iloc[-1] < data["close"].iloc[-20],
            # Eenvoudige trendfilter
        }

        # Genereer signaal
        return self._generate_signal(symbol, data, indicators, current_direction)

    def _generate_signal(self, symbol: str, data: pd.DataFrame,
            indicators: Dict[str, Any], current_direction: Optional[str], ) -> Dict[
        str, Any]:
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
        vol_filter = indicators.get("vol_filter", True)

        signal = None
        meta = {}

        # Controleer volatiliteitsfilter eerst
        if self.use_vol_filter and not vol_filter:
            return {"symbol": symbol, "signal": None,
                "meta": {"reason": "insufficient_volatility"},
                "timestamp": datetime.now(), }

        # Entry logica - als we geen positie hebben
        if current_direction is None:
            # Long entry (breakout boven entry_high)
            if current_price > prev_entry_high and indicators.get("trend_up", True):
                signal = "BUY"
                entry_price = prev_entry_high
                stop_loss = entry_price - (2 * current_atr)
                meta = {"entry_price": entry_price, "stop_loss": stop_loss,
                    "reason": "long_entry_breakout", "atr": current_atr, }

            # Short entry (breakout onder entry_low)
            elif current_price < prev_entry_low and indicators.get("trend_down", True):
                signal = "SELL"
                entry_price = prev_entry_low
                stop_loss = entry_price + (2 * current_atr)
                meta = {"entry_price": entry_price, "stop_loss": stop_loss,
                    "reason": "short_entry_breakout", "atr": current_atr, }

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
            "timestamp": datetime.now(), }

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
            "vol_filter": data.get("vol_filter", pd.Series([True])).iloc[-1],
            "trend_up": data["close"].iloc[-1] > data["close"].iloc[-20],
            "trend_down": data["close"].iloc[-1] < data["close"].iloc[-20], },
            current_direction, )

    def get_name(self) -> str:
        """
        Geeft de naam van de strategie terug.

        Returns:
            Naam van de strategie
        """
        return "Moderne Turtle Trading Strategy"

    def execute_signal(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Voert een handelssignaal uit.

        Args:
            signal_data: Dictionary met signaalinformatie

        Returns:
            Dictionary met resultaat van de handelsactie
        """
        if not signal_data or not signal_data.get("signal"):
            return {"success": False, "reason": "no_signal"}

        symbol = signal_data["symbol"]
        signal = signal_data["signal"]
        meta = signal_data.get("meta", {})

        # Haal account informatie op
        try:
            account_info = self.connector.get_account_info()
            if not account_info or "balance" not in account_info:
                self.logger.error(f"Kon account informatie niet ophalen voor {symbol}")
                return {"success": False, "reason": "account_info_missing"}

            account_balance = account_info["balance"]
        except Exception as e:
            self.logger.error(f"Fout bij ophalen account informatie: {e}")
            return {"success": False, "reason": "account_error", "error": str(e)}

        # Verwerk entry signalen
        if signal in ["BUY", "SELL"]:
            entry_price = meta.get("entry_price", 0)
            stop_loss = meta.get("stop_loss", 0)

            if entry_price <= 0 or stop_loss <= 0:
                self.logger.warning(f"Ongeldige entry of stop-loss voor {symbol}")
                return {"success": False, "reason": "invalid_price_levels"}

            # Bereken positiegrootte
            position_size = self.risk_manager.calculate_position_size(account_balance,
                entry_price, stop_loss)

            if position_size <= 0:
                self.logger.warning(
                    f"Ongeldige positiegrootte voor {symbol}: {position_size}")
                return {"success": False, "reason": "invalid_position_size"}

            # Plaats order
            try:
                order_result = self.connector.place_order(symbol, signal, position_size,
                    entry_price, stop_loss,
                    entry_price * 1.5 if signal == "BUY" else entry_price * 0.5,
                    # Take profit
                    f"Sophia Turtle {signal}", )

                if order_result and order_result.get("success"):
                    # Update positie tracking
                    self.positions[symbol] = {"direction": signal,
                        "entry_price": entry_price, "stop_loss": stop_loss,
                        "size": position_size, "entry_time": datetime.now(),
                        "order_id": order_result.get("order_id"), }

                    self.logger.info(
                        f"Order geplaatst: {signal} {position_size} lots {symbol} @ {entry_price} SL: {stop_loss}")
                    return {"success": True, "action": "entry", "order": order_result}
                else:
                    self.logger.error(
                        f"Order plaatsen mislukt voor {symbol}: {order_result}")
                    return {"success": False, "reason": "order_failed",
                        "details": order_result, }

            except Exception as e:
                self.logger.error(f"Fout bij order plaatsen voor {symbol}: {e}")
                return {"success": False, "reason": "order_error", "error": str(e)}

        # Verwerk exit signalen
        elif signal in ["CLOSE_BUY", "CLOSE_SELL"]:
            if symbol not in self.positions:
                self.logger.warning(f"Geen open positie gevonden voor {symbol}")
                return {"success": False, "reason": "no_position"}

            try:
                # In een echte implementatie zou je hier de positie sluiten via MT5
                # Voor nu sluiten we het alleen in onze tracking
                position_info = self.positions[symbol]

                # Voeg hier de code toe om de positie te sluiten via MT5
                # close_result = self.connector.close_position(symbol)

                # Voor nu simuleren we een succesvol resultaat
                close_result = {"success": True}

                if close_result and close_result.get("success"):
                    self.logger.info(f"Positie gesloten: {symbol}")
                    # Verwijder de positie uit tracking
                    del self.positions[symbol]
                    return {"success": True, "action": "exit", "order": close_result}
                else:
                    self.logger.error(f"Positie sluiten mislukt voor {symbol}")
                    return {"success": False, "reason": "close_failed",
                        "details": close_result, }

            except Exception as e:
                self.logger.error(f"Fout bij sluiten positie voor {symbol}: {e}")
                return {"success": False, "reason": "close_error", "error": str(e)}

        return {"success": False, "reason": "invalid_signal"}
