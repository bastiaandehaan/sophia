# src/strategy_ema.py
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd


class EMAStrategy:
    """
    EMA Crossover Trading Strategy voor MT5.
    Gebruikt dubbele EMA crossing met RSI filters voor bevestiging.
    """

    def __init__(self, connector, risk_manager, config):
        """
        Initialiseer de EMA Crossover strategie.

        Args:
            connector: Connector voor marktdata en order uitvoering
            risk_manager: Risk manager voor positiegrootte berekening
            config: Configuratie dictionary met strategie parameters
        """
        self.connector = connector
        self.risk_manager = risk_manager
        self.config = config
        self.logger = logging.getLogger("sophia.ema")

        # Strategie parameters
        self.fast_ema = config.get("fast_ema", 9)
        self.slow_ema = config.get("slow_ema", 21)
        self.signal_ema = config.get("signal_ema", 5)
        self.rsi_period = config.get("rsi_period", 14)
        self.rsi_upper = config.get("rsi_upper", 70)
        self.rsi_lower = config.get("rsi_lower", 30)
        self.atr_period = config.get("atr_period", 14)
        self.atr_multiplier = config.get("atr_multiplier", 2.0)

        # Tijdsfilter voor intraday trading
        self.use_time_filter = config.get("use_time_filter", False)
        self.session_start = config.get("session_start", 8)  # 8:00
        self.session_end = config.get("session_end", 16)  # 16:00

        # Positie tracking
        self.positions = {}

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Bereken indicators voor de EMA strategie.

        Args:
            data: DataFrame met historische prijsdata

        Returns:
            DataFrame met toegevoegde indicators
        """
        # Maak kopie om originele data niet te wijzigen
        df = data.copy()

        # Fast en Slow EMA
        df["fast_ema"] = df["close"].ewm(span=self.fast_ema,
                                         adjust=False).mean()
        df["slow_ema"] = df["close"].ewm(span=self.slow_ema,
                                         adjust=False).mean()

        # MACD en Signal Line
        df["macd"] = df["fast_ema"] - df["slow_ema"]
        df["signal"] = df["macd"].ewm(span=self.signal_ema, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["signal"]

        # RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=self.rsi_period).mean()
        avg_loss = loss.rolling(window=self.rsi_period).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # ATR berekening
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df["atr"] = true_range.rolling(window=self.atr_period).mean()

        # Momentum
        df["momentum"] = df["close"] / df["close"].shift(12) - 1

        # Bollinger Bands
        rolling_mean = df["close"].rolling(window=20).mean()
        rolling_std = df["close"].rolling(window=20).std()
        df["bollinger_mid"] = rolling_mean
        df["bollinger_upper"] = rolling_mean + (rolling_std * 2)
        df["bollinger_lower"] = rolling_mean - (rolling_std * 2)

        return df

    def check_signals(
            self, symbol: str, data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
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
            bars_needed = (
                    max(self.slow_ema, self.rsi_period) + 30
            )  # Extra bars voor goede berekening
            data = self.connector.get_historical_data(
                symbol, self.config.get("timeframe", "H4"), bars_needed
            )

            if data is None or len(data) < bars_needed:
                self.logger.error(f"Onvoldoende data beschikbaar voor {symbol}")
                return {
                    "symbol": symbol,
                    "signal": None,
                    "meta": {},
                    "timestamp": datetime.now(),
                }

        # Bereken indicators
        data = self.calculate_indicators(data)

        # Controleer of we een positie hebben
        position = self.positions.get(symbol)
        current_direction = position["direction"] if position else None

        # Controleer of huidige tijd binnen handelssessie valt als tijdsfilter actief is
        if self.use_time_filter:
            current_hour = datetime.now().hour
            if not (self.session_start <= current_hour < self.session_end):
                return {
                    "symbol": symbol,
                    "signal": None,
                    "meta": {"reason": "outside_trading_hours"},
                    "timestamp": datetime.now(),
                }

        # Verzamel indicators voor signaal generatie
        indicators = {
            "current_price": data["close"].iloc[-1],
            "fast_ema": data["fast_ema"].iloc[-1],
            "slow_ema": data["slow_ema"].iloc[-1],
            "macd": data["macd"].iloc[-1],
            "signal": data["signal"].iloc[-1],
            "macd_hist": data["macd_hist"].iloc[-1],
            "prev_macd_hist": data["macd_hist"].iloc[-2],
            "rsi": data["rsi"].iloc[-1],
            "atr": data["atr"].iloc[-1],
            "momentum": data["momentum"].iloc[-1],
            "bollinger_mid": data["bollinger_mid"].iloc[-1],
            "bollinger_upper": data["bollinger_upper"].iloc[-1],
            "bollinger_lower": data["bollinger_lower"].iloc[-1],
        }

        # Genereer signaal
        return self._generate_signal(symbol, data, indicators,
                                     current_direction)

    def _generate_signal(
            self,
            symbol: str,
            data: pd.DataFrame,
            indicators: Dict[str, Any],
            current_direction: Optional[str],
    ) -> Dict[str, Any]:
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
        fast_ema = indicators["fast_ema"]
        slow_ema = indicators["slow_ema"]
        macd = indicators["macd"]
        signal_line = indicators["signal"]
        macd_hist = indicators["macd_hist"]
        prev_macd_hist = indicators["prev_macd_hist"]
        rsi = indicators["rsi"]
        momentum = indicators["momentum"]
        atr_value = indicators["atr"]
        bollinger_mid = indicators["bollinger_mid"]

        signal = None
        meta = {}

        # Entry logica - als we geen positie hebben
        if current_direction is None:
            # Long entry:
            # 1. Fast EMA > Slow EMA (trend is up)
            # 2. MACD histogram draait positief (crossover)
            # 3. RSI > 50 (momentum bevestiging)
            # 4. Prijs boven midden Bollinger (extra filter)
            if (
                    fast_ema > slow_ema
                    and macd > signal_line
                    and macd_hist > 0
                    and prev_macd_hist <= 0  # Crossover
                    and rsi > 50
                    and momentum > 0
                    and current_price > bollinger_mid
            ):

                signal = "BUY"
                entry_price = current_price
                stop_loss = entry_price - (self.atr_multiplier * atr_value)
                meta = {
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "reason": "ema_macd_long_entry",
                    "atr": atr_value,
                }

            # Short entry:
            # 1. Fast EMA < Slow EMA (trend is down)
            # 2. MACD histogram draait negatief (crossover)
            # 3. RSI < 50 (momentum bevestiging)
            # 4. Prijs onder midden Bollinger (extra filter)
            elif (
                    fast_ema < slow_ema
                    and macd < signal_line
                    and macd_hist < 0
                    and prev_macd_hist >= 0  # Crossover
                    and rsi < 50
                    and momentum < 0
                    and current_price < bollinger_mid
            ):

                signal = "SELL"
                entry_price = current_price
                stop_loss = entry_price + (self.atr_multiplier * atr_value)
                meta = {
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "reason": "ema_macd_short_entry",
                    "atr": atr_value,
                }

        # Exit logica - voor bestaande posities
        elif current_direction == "BUY":
            # Exit long positie als MACD onder signaal lijn kruist of EMA crossover
            if (
                    macd < signal_line and macd_hist < 0 and prev_macd_hist >= 0
            ) or fast_ema < slow_ema:
                signal = "CLOSE_BUY"
                meta = {"reason": "ema_macd_long_exit"}

        elif current_direction == "SELL":
            # Exit short positie als MACD boven signaal lijn kruist of EMA crossover
            if (
                    macd > signal_line and macd_hist > 0 and prev_macd_hist <= 0
            ) or fast_ema > slow_ema:
                signal = "CLOSE_SELL"
                meta = {"reason": "ema_macd_short_exit"}

        if signal:
            self.logger.info(
                f"Signaal voor {symbol}: {signal} - {meta.get('reason')}")

        return {
            "symbol": symbol,
            "signal": signal,
            "meta": meta,
            "timestamp": datetime.now(),
        }

    def get_name(self) -> str:
        """
        Geeft de naam van de strategie terug.

        Returns:
            Naam van de strategie
        """
        return "EMA Crossover met MACD Strategy"

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
                self.logger.error(
                    f"Kon account informatie niet ophalen voor {symbol}")
                return {"success": False, "reason": "account_info_missing"}

            account_balance = account_info["balance"]
        except Exception as e:
            self.logger.error(f"Fout bij ophalen account informatie: {e}")
            return {"success": False, "reason": "account_error",
                    "error": str(e)}

        # Verwerk entry signalen
        if signal in ["BUY", "SELL"]:
            entry_price = meta.get("entry_price", 0)
            stop_loss = meta.get("stop_loss", 0)

            if entry_price <= 0 or stop_loss <= 0:
                self.logger.warning(
                    f"Ongeldige entry of stop-loss voor {symbol}")
                return {"success": False, "reason": "invalid_price_levels"}

            # Bereken positiegrootte
            position_size = self.risk_manager.calculate_position_size(
                account_balance, entry_price, stop_loss, symbol
            )

            if position_size <= 0:
                self.logger.warning(
                    f"Ongeldige positiegrootte voor {symbol}: {position_size}"
                )
                return {"success": False, "reason": "invalid_position_size"}

            # Berekenen take profit op basis van ATR
            atr_value = meta.get("atr", 0)
            if atr_value > 0:
                # Profit target = 3x risico (ATR_multiplier)
                profit_multiplier = self.config.get("profit_multiplier", 3.0)
                if signal == "BUY":
                    take_profit = entry_price + (
                            self.atr_multiplier * profit_multiplier * atr_value
                    )
                else:  # SELL
                    take_profit = entry_price - (
                            self.atr_multiplier * profit_multiplier * atr_value
                    )
            else:
                # Fallback als geen ATR beschikbaar is
                if signal == "BUY":
                    take_profit = entry_price * 1.01  # 1% winst
                else:
                    take_profit = entry_price * 0.99  # 1% winst

            # Plaats order
            try:
                order_result = self.connector.place_order(
                    symbol,
                    signal,
                    position_size,
                    entry_price,
                    stop_loss,
                    take_profit,
                    f"Sophia EMA {signal}",
                )

                if order_result and order_result.get("success"):
                    # Update positie tracking
                    self.positions[symbol] = {
                        "direction": signal,
                        "entry_price": entry_price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "size": position_size,
                        "entry_time": datetime.now(),
                        "order_id": order_result.get("order_id"),
                    }

                    self.logger.info(
                        f"Order geplaatst: {signal} {position_size} lots {symbol} @ {entry_price} "
                        f"SL: {stop_loss} TP: {take_profit}"
                    )
                    return {"success": True, "action": "entry",
                            "order": order_result}
                else:
                    self.logger.error(
                        f"Order plaatsen mislukt voor {symbol}: {order_result}"
                    )
                    return {
                        "success": False,
                        "reason": "order_failed",
                        "details": order_result,
                    }

            except Exception as e:
                self.logger.error(f"Fout bij order plaatsen voor {symbol}: {e}")
                return {"success": False, "reason": "order_error",
                        "error": str(e)}

        # Verwerk exit signalen
        elif signal in ["CLOSE_BUY", "CLOSE_SELL"]:
            if symbol not in self.positions:
                self.logger.warning(f"Geen open positie gevonden voor {symbol}")
                return {"success": False, "reason": "no_position"}

            try:
                # Sluit de positie via connector
                close_result = self.connector.close_position(symbol)

                if close_result and close_result.get("success"):
                    self.logger.info(f"Positie gesloten: {symbol}")
                    # Verwijder de positie uit tracking
                    del self.positions[symbol]
                    return {"success": True, "action": "exit",
                            "order": close_result}
                else:
                    self.logger.error(f"Positie sluiten mislukt voor {symbol}")
                    return {
                        "success": False,
                        "reason": "close_failed",
                        "details": close_result,
                    }

            except Exception as e:
                self.logger.error(
                    f"Fout bij sluiten positie voor {symbol}: {e}")
                return {"success": False, "reason": "close_error",
                        "error": str(e)}

        return {"success": False, "reason": "invalid_signal"}
