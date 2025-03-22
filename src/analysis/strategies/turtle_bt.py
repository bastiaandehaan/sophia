#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Turtle Trading Strategy voor Backtrader.
Gebaseerd op de originele Turtle Trading regels maar gemoderniseerd
met een volatiliteitsfilter.
"""

import logging

import backtrader as bt
import backtrader.indicators as btind


class TurtleStrategy(bt.Strategy):
    """
    Backtrader implementatie van de klassieke Turtle Trading strategie.

    Parameters:
    - entry_period: Periode voor entry Donchian channel (standaard: 20)
    - exit_period: Periode voor exit Donchian channel (standaard: 10)
    - atr_period: Periode voor ATR berekening (standaard: 14)
    - risk_pct: Percentage van kapitaal om te riskeren per trade (standaard: 1%)
    - use_vol_filter: Of volatiliteitsfilter gebruikt moet worden (standaard: True)
    - vol_lookback: Lookback periode voor volatiliteitsfilter (standaard: 100)
    - vol_threshold: Drempelwaarde voor volatiliteitsfilter (standaard: 1.2)
    """

    params = (
        ("entry_period", 20),  # Entry Donchian channel periode
        ("exit_period", 10),  # Exit Donchian channel periode
        ("atr_period", 14),  # ATR periode
        ("risk_pct", 0.01),  # Percentage risico per trade (1%)
        ("use_vol_filter", True),  # Gebruik volatiliteitsfilter
        ("vol_lookback", 100),  # Lookback periode voor vol filter
        ("vol_threshold", 1.2),  # Drempelwaarde voor vol filter
        ("trend_filter", True),  # Gebruik trendfilter
        ("trend_period", 200),  # Periode voor trendfilter SMA
        ("pyramiding", 1),  # Maximum aantal posities per richting
    )

    def __init__(self):
        """Initialiseer de Turtle strategie met indicators."""
        self.logger = logging.getLogger("sophia.backtrader.turtle")

        # Dictionary om posities bij te houden per data/symbool
        self._positions = {}  # Verander naar _positions (private)
        self.orders = {}

        # Indicators per data feed
        self.inds = {}

        # Minimale aantallen bars nodig voor betrouwbare berekeningen
        self.min_bars_required = max(
            self.params.entry_period,
            self.params.exit_period,
            self.params.atr_period
        ) + 5  # Extra marge voor veiligheid

        # Interne state tracking
        self.ready_for_trading = {}

        # Loop over alle data feeds en maak indicators aan
        for i, data in enumerate(self.datas):
            self._positions[data._name] = 0  # Gebruik _positions
            self.orders[data._name] = None
            self.ready_for_trading[data._name] = False

            # Entry Donchian Channel (hoogste high en laagste low over entry_period)
            entry_high = btind.Highest(data.high,
                                       period=self.params.entry_period)
            entry_low = btind.Lowest(data.low, period=self.params.entry_period)

            # Exit Donchian Channel (hoogste high en laagste low over exit_period)
            exit_high = btind.Highest(data.high, period=self.params.exit_period)
            exit_low = btind.Lowest(data.low, period=self.params.exit_period)

            # Average True Range voor volatiliteit
            atr = btind.ATR(data, period=self.params.atr_period)

            # Volatiliteitsfilter - vergelijk huidige ATR met historisch gemiddelde
            if self.params.use_vol_filter and self.params.vol_lookback > 0:
                atr_avg = btind.SMA(atr, period=self.params.vol_lookback)
                vol_filter = atr > atr_avg * self.params.vol_threshold
            else:
                vol_filter = None

            # Trendfilter met SMA
            if self.params.trend_filter:
                sma = btind.SMA(data, period=self.params.trend_period)
                trend_up = data.close > sma
                trend_down = data.close < sma
            else:
                trend_up = None
                trend_down = None

            # Sla indicators op per symbool
            self.inds[data._name] = {
                "entry_high": entry_high,
                "entry_low": entry_low,
                "exit_high": exit_high,
                "exit_low": exit_low,
                "atr": atr,
                "vol_filter": vol_filter,
                "trend_up": trend_up,
                "trend_down": trend_down,
            }

            self.logger.info(f"Initialized Turtle strategy for {data._name}")

    # Voeg prenext methode toe om array-indexeringsproblemen te voorkomen
    def prenext(self):
        """
        Wordt aangeroepen wanneer er onvoldoende data beschikbaar is.
        Voorkomt handelingen met incomplete datasets.
        """
        # Skip alle berekeningen tijdens deze fase
        pass

    # Voeg deze property en setter toe om het probleem op te lossen
    @property
    def positions(self):
        """Get positions dictionary."""
        return self._positions

    @positions.setter
    def positions(self, value):
        """Set positions dictionary."""
        self._positions = value

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
        found_symbol = None
        for data_name, ord in self.orders.items():
            if ord is not None and order.ref == ord.ref:
                # Order is van dit symbool
                found_symbol = data_name
                break

        if found_symbol is None:
            # Order niet gevonden, waarschijnlijk een verouderd order
            return

        symbol = found_symbol  # Gebruik de gevonden waarde

        # Controleer of het order is voltooid
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED for {symbol}, Price: {order.executed.price:.5f}, "
                    f"Size: {order.executed.size:.2f}"
                )
                self._positions[symbol] = 1
            elif order.issell():
                self.log(
                    f"SELL EXECUTED for {symbol}, Price: {order.executed.price:.5f}, "
                    f"Size: {order.executed.size:.2f}"
                )
                self._positions[symbol] = -1

            # Reset order referentie
            self.orders[symbol] = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected for {symbol}")
            # Reset order referentie
            self.orders[symbol] = None

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

    def next(self):
        """
        Core methode die elke bar wordt uitgevoerd om signalen te detecteren
        en orders te plaatsen.
        """
        # Loop over alle data feeds
        for i, data in enumerate(self.datas):
            symbol = data._name

            # Controleer of we voldoende data hebben voor betrouwbare berekeningen
            if not self.ready_for_trading.get(symbol, False):
                if len(data) >= self.min_bars_required:
                    self.ready_for_trading[symbol] = True
                    self.log(f"Strategie is nu klaar voor trading op {symbol}")
                else:
                    continue  # Skip tot we voldoende historische data hebben

            # Veilig ophalen van positie- en indicator-data
            pos = self._positions.get(symbol, 0)
            inds = self.inds.get(symbol, {})

            # Skip als er al een pending order is
            if self.orders.get(symbol) is not None:
                continue

            try:
                # Gebruik veilige array toegang
                current_price = data.close[0]

                # Veiligere indexering
                if i < len(data) - 1:  # Controleer of er vorige bars zijn
                    prev_entry_high = inds["entry_high"][-2] if len(
                        inds["entry_high"]) > 1 else None
                    prev_entry_low = inds["entry_low"][-2] if len(
                        inds["entry_low"]) > 1 else None
                    prev_exit_high = inds["exit_high"][-2] if len(
                        inds["exit_high"]) > 1 else None
                    prev_exit_low = inds["exit_low"][-2] if len(
                        inds["exit_low"]) > 1 else None
                else:
                    # Niet genoeg history
                    continue

                # Extra veiligheidscontrole
                if None in (
                    prev_entry_high, prev_entry_low, prev_exit_high,
                    prev_exit_low):
                    continue

                # Controleer volatiliteitsfilter (indien actief)
                vol_filter_passed = True
                if "vol_filter" in inds and inds["vol_filter"] is not None:
                    # Try-except om array indexing errors op te vangen
                    try:
                        vol_filter_passed = bool(inds["vol_filter"][0])
                    except:
                        vol_filter_passed = True  # Fallback naar True als er een error is

                # Controleer trendfilter (indien actief)
                trend_up = True
                trend_down = True
                if "trend_up" in inds and inds["trend_up"] is not None:
                    try:
                        trend_up = bool(inds["trend_up"][0])
                    except:
                        trend_up = True
                if "trend_down" in inds and inds["trend_down"] is not None:
                    try:
                        trend_down = bool(inds["trend_down"][0])
                    except:
                        trend_down = True

                # Entry logica als we geen positie hebben
                if pos == 0:
                    # Long entry (breakout boven entry_high)
                    if current_price > prev_entry_high and vol_filter_passed and trend_up:
                        # Calculate position size based on ATR for risk management
                        atr_value = inds["atr"][0]
                        stop_price = current_price - (2 * atr_value)

                        self.log(
                            f"BUY SIGNAL for {symbol} at {current_price:.5f}, "
                            f"Stop: {stop_price:.5f}"
                        )

                        # Place buy order
                        self.orders[symbol] = self.buy(data=data)
                        self._positions[symbol] = 1

                    # Short entry (breakout onder entry_low)
                    elif (
                        current_price < prev_entry_low and vol_filter_passed and trend_down
                    ):
                        # Calculate position size based on ATR for risk management
                        atr_value = inds["atr"][0]
                        stop_price = current_price + (2 * atr_value)

                        self.log(
                            f"SELL SIGNAL for {symbol} at {current_price:.5f}, "
                            f"Stop: {stop_price:.5f}"
                        )

                        # Place sell order
                        self.orders[symbol] = self.sell(data=data)
                        self._positions[symbol] = -1

                # Exit logica voor bestaande posities
                elif pos > 0:  # Long positie
                    # Exit long positie als prijs onder exit_low daalt
                    if current_price < prev_exit_low:
                        self.log(
                            f"CLOSE LONG for {symbol} at {current_price:.5f}")

                        # Close long position
                        self.orders[symbol] = self.close(data=data)
                        self._positions[symbol] = 0

                elif pos < 0:  # Short positie
                    # Exit short positie als prijs boven exit_high stijgt
                    if current_price > prev_exit_high:
                        self.log(
                            f"CLOSE SHORT for {symbol} at {current_price:.5f}")

                        # Close short position
                        self.orders[symbol] = self.close(data=data)
                        self._positions[symbol] = 0

            except Exception as e:
                self.log(f"Fout tijdens verwerken van data voor {symbol}: {e}")
                continue

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
