#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Intraday EMA Trading Strategy voor Backtrader.
Gebaseerd op cross-over van twee EMA's met RSI-filter voor bevestiging.
"""

import logging
from typing import Dict, Any, Optional

import backtrader as bt
import backtrader.indicators as btind


class EMAStrategy(bt.Strategy):
    """
    Backtrader implementatie van een Intraday EMA Trading strategie.

    Parameters:
    - fast_ema: Periode voor snelle EMA (standaard: 9)
    - slow_ema: Periode voor trage EMA (standaard: 21)
    - signal_ema: Periode voor signaal EMA (standaard: 5)
    - rsi_period: Periode voor RSI (standaard: 14)
    - rsi_upper: Bovengrens voor RSI (standaard: 70)
    - rsi_lower: Ondergrens voor RSI (standaard: 30)
    - atr_period: Periode voor ATR berekening (standaard: 14)
    - atr_multiplier: Vermenigvuldiger voor ATR bij stop loss (standaard: 2.0)
    - risk_pct: Percentage van kapitaal om te riskeren per trade (standaard: 1%)
    - trail_stop: Activeer trailing stop (standaard: True)
    """

    # Backtrader parameters must be defined this way
    params = (
        ("fast_ema", 9),         # Snelle EMA periode
        ("slow_ema", 21),        # Trage EMA periode
        ("signal_ema", 5),       # Signaal EMA periode
        ("rsi_period", 14),      # RSI periode
        ("rsi_upper", 70),       # RSI bovengrens
        ("rsi_lower", 30),       # RSI ondergrens
        ("atr_period", 14),      # ATR periode
        ("atr_multiplier", 2.0), # Stop loss ATR vermenigvuldiger
        ("risk_pct", 0.01),      # Risico percentage (1%)
        ("trail_stop", True),    # Gebruik trailing stop
        ("profit_target", 3.0),  # Winst target als ATR multiplier
        ("use_time_filter", True), # Gebruik tijdsfilter voor intraday trading
        ("session_start", 8),    # Sessie start (uur, bijv. 8 = 8:00)
        ("session_end", 16),     # Sessie einde (uur, bijv. 16 = 16:00)
    )

    def __init__(self):
        """Initialiseer de EMA strategie met indicators."""
        self.logger = logging.getLogger("sophia.backtrader.ema")

        # Dictionary om posities en stop losses bij te houden per data/symbool
        self.positions = {}
        self.orders = {}
        self.stop_orders = {}
        self.target_orders = {}
        self.stop_prices = {}

        # Indicators per data feed
        self.inds = {}

        # Loop over alle data feeds en maak indicators aan
        for i, data in enumerate(self.datas):
            self.positions[data._name] = 0
            self.orders[data._name] = None
            self.stop_orders[data._name] = None
            self.target_orders[data._name] = None
            self.stop_prices[data._name] = 0.0

            # EMA indicators
            fast_ema = btind.EMA(data, period=self.p.fast_ema)
            slow_ema = btind.EMA(data, period=self.p.slow_ema)

            # MACD voor betere signalen
            macd = fast_ema - slow_ema
            signal = btind.EMA(macd, period=self.p.signal_ema)
            macd_hist = macd - signal

            # RSI voor filtering
            rsi = btind.RSI(data, period=self.p.rsi_period)

            # ATR voor stop loss bepaling
            atr = btind.ATR(data, period=self.p.atr_period)

            # Momentum indicator
            mom = btind.Momentum(data.close, period=12)

            # Bollinger Bands voor volatiliteit
            boll = btind.BollingerBands(data, period=20, devfactor=2)

            # Sla indicators op per symbool
            self.inds[data._name] = {
                "fast_ema": fast_ema,
                "slow_ema": slow_ema,
                "macd": macd,
                "signal": signal,
                "macd_hist": macd_hist,
                "rsi": rsi,
                "atr": atr,
                "momentum": mom,
                "bollinger": boll,
            }

            self.logger.info(f"Initialized EMA strategy for {data._name}")

    def log(self, txt, dt=None):
        """Log bericht met timestamp."""
        dt = dt or self.datas[0].datetime.date(0)
        self.logger.info(f"{dt.isoformat()} {txt}")

    def notify_order(self, order):
        """
        Notificatie wanneer een order status wijzigt.

        Args:
            order: Backtrader Order object
        """
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted - wacht op uitvoering
            return

        # Vind het symbool voor dit order
        symbol = None
        order_type = "main"

        # Check regular orders
        for data_name, ord in self.orders.items():
            if ord is not None and order.ref == ord.ref:
                symbol = data_name
                order_type = "main"
                break

        # Check stop orders
        if symbol is None:
            for data_name, ord in self.stop_orders.items():
                if ord is not None and order.ref == ord.ref:
                    symbol = data_name
                    order_type = "stop"
                    break

        # Check target orders
        if symbol is None:
            for data_name, ord in self.target_orders.items():
                if ord is not None and order.ref == ord.ref:
                    symbol = data_name
                    order_type = "target"
                    break

        if symbol is None:
            # Order niet gevonden, waarschijnlijk een verouderd order
            return

        # Controleer of het order is voltooid
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED for {symbol}, Price: {order.executed.price:.5f}, "
                    f"Size: {order.executed.size:.2f}"
                )
                if order_type == "main":
                    self.positions[symbol] = 1

                    # Plaats stop loss en profit target
                    if self.p.trail_stop:
                        self._set_stop_loss(symbol)
                        self._set_profit_target(symbol)

            elif order.issell():
                self.log(
                    f"SELL EXECUTED for {symbol}, Price: {order.executed.price:.5f}, "
                    f"Size: {order.executed.size:.2f}"
                )
                if order_type == "main":
                    self.positions[symbol] = -1

                    # Plaats stop loss en profit target
                    if self.p.trail_stop:
                        self._set_stop_loss(symbol)
                        self._set_profit_target(symbol)

            # Reset order referentie
            if order_type == "main":
                self.orders[symbol] = None
            elif order_type == "stop":
                self.stop_orders[symbol] = None
                self.positions[symbol] = 0  # Reset positie als stop is geraakt
            elif order_type == "target":
                self.target_orders[symbol] = None
                self.positions[
                    symbol] = 0  # Reset positie als target is bereikt

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected for {symbol}")

            # Reset order referentie
            if order_type == "main":
                self.orders[symbol] = None
            elif order_type == "stop":
                self.stop_orders[symbol] = None
            elif order_type == "target":
                self.target_orders[symbol] = None

    def notify_trade(self, trade):
        """
        Notificatie wanneer een trade wordt gesloten.

        Args:
            trade: Backtrader Trade object
        """
        if not trade.isclosed:
            return

        # Vind de data/symbool voor deze trade
        data_name = trade.data._name

        self.log(
            f"TRADE COMPLETED for {data_name}, Profit: {trade.pnl:.2f}, "
            f"Net: {trade.pnlcomm:.2f}"
        )

    def _set_stop_loss(self, symbol):
        """
        Plaats een stop loss order voor het gegeven symbool.

        Args:
            symbol: Handelssymbool
        """
        # Vind de data voor dit symbool
        for data in self.datas:
            if data._name == symbol:
                break
        else:
            return

        # Bepaal stop loss prijs gebaseerd op ATR
        atr_value = self.inds[symbol]["atr"][0]
        current_price = data.close[0]

        if self.positions[symbol] > 0:  # Long positie
            stop_price = current_price - (
                    self.p.atr_multiplier * atr_value)
            self.stop_prices[symbol] = stop_price

            # Plaats stop order
            self.stop_orders[symbol] = self.sell(
                data=data,
                size=None,
                # Sluit hele positie
                exectype=bt.Order.Stop,
                price=stop_price,
            )

            self.log(f"STOP LOSS SET for {symbol} at {stop_price:.5f}")

        elif self.positions[symbol] < 0:  # Short positie
            stop_price = current_price + (
                    self.p.atr_multiplier * atr_value)
            self.stop_prices[symbol] = stop_price

            # Plaats stop order
            self.stop_orders[symbol] = self.buy(
                data=data,
                size=None,
                # Sluit hele positie
                exectype=bt.Order.Stop,
                price=stop_price,
            )

            self.log(f"STOP LOSS SET for {symbol} at {stop_price:.5f}")

    def _set_profit_target(self, symbol):
        """
        Plaats een profit target order voor het gegeven symbool.

        Args:
            symbol: Handelssymbool
        """
        # Vind de data voor dit symbool
        for data in self.datas:
            if data._name == symbol:
                break
        else:
            return

        # Bepaal target prijs gebaseerd op ATR
        atr_value = self.inds[symbol]["atr"][0]
        current_price = data.close[0]

        if self.positions[symbol] > 0:  # Long positie
            target_price = current_price + (
                    self.p.profit_target * atr_value)

            # Plaats limit order
            self.target_orders[symbol] = self.sell(
                data=data,
                size=None,
                # Sluit hele positie
                exectype=bt.Order.Limit,
                price=target_price,
            )

            self.log(f"PROFIT TARGET SET for {symbol} at {target_price:.5f}")

        elif self.positions[symbol] < 0:  # Short positie
            target_price = current_price - (
                    self.p.profit_target * atr_value)

            # Plaats limit order
            self.target_orders[symbol] = self.buy(
                data=data,
                size=None,
                # Sluit hele positie
                exectype=bt.Order.Limit,
                price=target_price,
            )

            self.log(f"PROFIT TARGET SET for {symbol} at {target_price:.5f}")

    def _update_trailing_stop(self, symbol):
        """
        Update trailing stop voor het gegeven symbool.

        Args:
            symbol: Handelssymbool
        """
        # Vind de data voor dit symbool
        for data in self.datas:
            if data._name == symbol:
                break
        else:
            return

        # Bereken nieuwe stop loss prijs
        atr_value = self.inds[symbol]["atr"][0]
        current_price = data.close[0]

        if self.positions[symbol] > 0:  # Long positie
            new_stop = current_price - (self.p.atr_multiplier * atr_value)

            # Update alleen als nieuwe stop hoger is dan huidige
            if new_stop > self.stop_prices[symbol]:
                # Cancel oude stop order
                if self.stop_orders[symbol] is not None:
                    self.cancel(self.stop_orders[symbol])
                    self.stop_orders[symbol] = None

                # Plaats nieuwe stop order
                self.stop_prices[symbol] = new_stop
                self.stop_orders[symbol] = self.sell(
                    data=data,
                    size=None,
                    # Sluit hele positie
                    exectype=bt.Order.Stop,
                    price=new_stop,
                )

                self.log(
                    f"TRAILING STOP UPDATED for {symbol} to {new_stop:.5f}")

        elif self.positions[symbol] < 0:  # Short positie
            new_stop = current_price + (self.p.atr_multiplier * atr_value)

            # Update alleen als nieuwe stop lager is dan huidige
            if new_stop < self.stop_prices[symbol]:
                # Cancel oude stop order
                if self.stop_orders[symbol] is not None:
                    self.cancel(self.stop_orders[symbol])
                    self.stop_orders[symbol] = None

                # Plaats nieuwe stop order
                self.stop_prices[symbol] = new_stop
                self.stop_orders[symbol] = self.buy(
                    data=data,
                    size=None,
                    # Sluit hele positie
                    exectype=bt.Order.Stop,
                    price=new_stop,
                )

                self.log(
                    f"TRAILING STOP UPDATED for {symbol} to {new_stop:.5f}")

    def _is_in_session(self, data):
        """
        Controleer of de huidige tijd binnen de handelssessie valt.

        Args:
            data: Backtrader Data feed

        Returns:
            bool: True als binnen sessie, anders False
        """
        if not self.p.use_time_filter:
            return True

        # Haal huidige tijd op
        current_time = bt.num2date(data.datetime[0])
        hour = current_time.hour

        # Controleer of tijd binnen sessie valt
        return self.p.session_start <= hour < self.p.session_end

    def next(self):
        """
        Core methode die elke bar wordt uitgevoerd om signalen te detecteren
        en orders te plaatsen.
        """
        # Loop over alle data feeds
        for i, data in enumerate(self.datas):
            symbol = data._name
            pos = self.positions[symbol]
            inds = self.inds[symbol]

            # Skip als er al een pending order is
            if self.orders[symbol] is not None:
                continue

            # Update trailing stop voor bestaande posities
            if pos != 0 and self.p.trail_stop:
                self._update_trailing_stop(symbol)

            # Check of we binnen handelssessie zijn
            if not self._is_in_session(data):
                # Eventueel posities sluiten aan einde sessie
                if (
                    pos != 0
                    and data.datetime.time().hour >= self.p.session_end - 1
                ):
                    self.log(f"SESSION END: Closing position for {symbol}")
                    self.close(data=data)
                    self.positions[symbol] = 0
                continue

            # Huidige indicator waarden
            fast_ema = inds["fast_ema"][0]
            slow_ema = inds["slow_ema"][0]
            macd = inds["macd"][0]
            signal = inds["signal"][0]
            macd_hist = inds["macd_hist"][0]
            rsi = inds["rsi"][0]
            momentum = inds["momentum"][0]
            boll_mid = inds["bollinger"].mid[0]
            boll_top = inds["bollinger"].top[0]
            boll_bot = inds["bollinger"].bot[0]

            # Vorige waarden
            prev_macd_hist = inds["macd_hist"][-1]

            # Entry logica als we geen positie hebben
            if pos == 0:
                # Long entry:
                # 1. Fast EMA > Slow EMA (trend is up)
                # 2. MACD histogram draait positief (crossover)
                # 3. RSI > 50 (momentum bevestiging)
                if (
                    fast_ema > slow_ema
                    and macd > signal
                    and macd_hist > 0
                    and prev_macd_hist <= 0  # Crossover
                    and rsi > 50
                    and momentum > 0
                    and data.close[0] > boll_mid
                ):  # Prijs boven midden Bollinger

                    self.log(f"BUY SIGNAL for {symbol} at {data.close[0]:.5f}")

                    # Place buy order
                    self.orders[symbol] = self.buy(data=data)

                # Short entry:
                # 1. Fast EMA < Slow EMA (trend is down)
                # 2. MACD histogram draait negatief (crossover)
                # 3. RSI < 50 (momentum bevestiging)
                elif (
                    fast_ema < slow_ema
                    and macd < signal
                    and macd_hist < 0
                    and prev_macd_hist >= 0  # Crossover
                    and rsi < 50
                    and momentum < 0
                    and data.close[0] < boll_mid
                ):  # Prijs onder midden Bollinger

                    self.log(f"SELL SIGNAL for {symbol} at {data.close[0]:.5f}")

                    # Place sell order
                    self.orders[symbol] = self.sell(data=data)

            # Exit logica voor bestaande posities (naast stop loss/take profit)
            elif pos > 0:  # Long positie
                # Exit als MACD onder signaal lijn kruist of EMA crossover
                if (
                    macd < signal and macd_hist < 0 and prev_macd_hist >= 0
                ) or fast_ema < slow_ema:
                    self.log(f"CLOSE LONG for {symbol} at {data.close[0]:.5f}")

                    # Cancel bestaande stop en target orders
                    if self.stop_orders[symbol] is not None:
                        self.cancel(self.stop_orders[symbol])
                        self.stop_orders[symbol] = None

                    if self.target_orders[symbol] is not None:
                        self.cancel(self.target_orders[symbol])
                        self.target_orders[symbol] = None

                    # Close long position
                    self.close(data=data)
                    self.positions[symbol] = 0

            elif pos < 0:  # Short positie
                # Exit als MACD boven signaal lijn kruist of EMA crossover
                if (
                    macd > signal and macd_hist > 0 and prev_macd_hist <= 0
                ) or fast_ema > slow_ema:
                    self.log(f"CLOSE SHORT for {symbol} at {data.close[0]:.5f}")

                    # Cancel bestaande stop en target orders
                    if self.stop_orders[symbol] is not None:
                        self.cancel(self.stop_orders[symbol])
                        self.stop_orders[symbol] = None

                    if self.target_orders[symbol] is not None:
                        self.cancel(self.target_orders[symbol])
                        self.target_orders[symbol] = None

                    # Close short position
                    self.close(data=data)
                    self.positions[symbol] = 0

    def stop(self):
        """
        Wordt aangeroepen aan het einde van de backtest om resultaten te loggen.
        """
        self.log("Backtest completed")

        # Log de final portfolio waarde
        portfolio_value = self.broker.getvalue()
        initial_value = self.broker.startingcash
        profit_pct = (portfolio_value / initial_value - 1.0) * 100

        self.log(f"Final Portfolio Value: {portfolio_value:.2f}")
        self.log(f"Profit/Loss: {profit_pct:.2f}%")