#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Intraday EMA Trading Strategy voor Backtrader.
Gebaseerd op cross-over van twee EMA's met RSI-filter voor bevestiging.
"""

import logging

import backtrader as bt
import backtrader.indicators as btind


class EMAStrategy(bt.Strategy):
    params = (
        ("fast_ema", 9),
        ("slow_ema", 21),
        ("signal_ema", 5),
        ("rsi_period", 14),
        ("rsi_upper", 70),
        ("rsi_lower", 30),
        ("atr_period", 14),
        ("atr_multiplier", 2.0),
        ("risk_pct", 0.01),
        ("trail_stop", True),
        ("profit_target", 3.0),
        ("use_time_filter", True),
        ("session_start", 8),
        ("session_end", 16),
    )

    def __init__(self):
        """Initialiseer de EMA strategie met indicators."""
        self.logger = logging.getLogger("sophia.backtrader.ema")

        # Gebruik een eigen dictionary voor trade posities
        self.trade_positions = {}  # Vervangt self.positions
        self.orders = {}
        self.stop_orders = {}
        self.target_orders = {}
        self.stop_prices = {}

        # Indicators per data feed
        self.inds = {}

        # Loop over alle data feeds en maak indicators aan
        for i, data in enumerate(self.datas):
            self.trade_positions[data._name] = 0  # Eigen tracking
            self.orders[data._name] = None
            self.stop_orders[data._name] = None
            self.target_orders[data._name] = None
            self.stop_prices[data._name] = 0.0

            # EMA indicators
            fast_ema = btind.EMA(data, period=self.p.fast_ema)
            slow_ema = btind.EMA(data, period=self.p.slow_ema)
            macd = fast_ema - slow_ema
            signal = btind.EMA(macd, period=self.p.signal_ema)
            macd_hist = macd - signal
            rsi = btind.RSI(data, period=self.p.rsi_period)
            atr = btind.ATR(data, period=self.p.atr_period)
            mom = btind.Momentum(data.close, period=12)
            boll = btind.BollingerBands(data, period=20, devfactor=2)

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
        dt = dt or self.datas[0].datetime.date(0)
        self.logger.info(f"{dt.isoformat()} {txt}")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        symbol = None
        order_type = "main"
        for data_name, ord in self.orders.items():
            if ord is not None and order.ref == ord.ref:
                symbol = data_name
                order_type = "main"
                break
        if symbol is None:
            for data_name, ord in self.stop_orders.items():
                if ord is not None and order.ref == ord.ref:
                    symbol = data_name
                    order_type = "stop"
                    break
        if symbol is None:
            for data_name, ord in self.target_orders.items():
                if ord is not None and order.ref == ord.ref:
                    symbol = data_name
                    order_type = "target"
                    break

        if symbol is None:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED for {symbol}, Price: {order.executed.price:.5f}, "
                    f"Size: {order.executed.size:.2f}"
                )
                if order_type == "main":
                    self.trade_positions[symbol] = 1  # Gebruik trade_positions
                    if self.p.trail_stop:
                        self._set_stop_loss(symbol)
                        self._set_profit_target(symbol)
            elif order.issell():
                self.log(
                    f"SELL EXECUTED for {symbol}, Price: {order.executed.price:.5f}, "
                    f"Size: {order.executed.size:.2f}"
                )
                if order_type == "main":
                    self.trade_positions[symbol] = -1  # Gebruik trade_positions
                    if self.p.trail_stop:
                        self._set_stop_loss(symbol)
                        self._set_profit_target(symbol)

            if order_type == "main":
                self.orders[symbol] = None
            elif order_type == "stop":
                self.stop_orders[symbol] = None
                self.trade_positions[symbol] = 0  # Reset
            elif order_type == "target":
                self.target_orders[symbol] = None
                self.trade_positions[symbol] = 0  # Reset

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected for {symbol}")
            if order_type == "main":
                self.orders[symbol] = None
            elif order_type == "stop":
                self.stop_orders[symbol] = None
            elif order_type == "target":
                self.target_orders[symbol] = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        data_name = trade.data._name
        self.log(
            f"TRADE COMPLETED for {data_name}, Profit: {trade.pnl:.2f}, "
            f"Net: {trade.pnlcomm:.2f}"
        )

    def _set_stop_loss(self, symbol):
        for data in self.datas:
            if data._name == symbol:
                break
        else:
            return
        atr_value = self.inds[symbol]["atr"][0]
        current_price = data.close[0]
        if self.trade_positions[symbol] > 0:  # Long
            stop_price = current_price - (self.p.atr_multiplier * atr_value)
            self.stop_prices[symbol] = stop_price
            self.stop_orders[symbol] = self.sell(
                data=data, exectype=bt.Order.Stop, price=stop_price
            )
            self.log(f"STOP LOSS SET for {symbol} at {stop_price:.5f}")
        elif self.trade_positions[symbol] < 0:  # Short
            stop_price = current_price + (self.p.atr_multiplier * atr_value)
            self.stop_prices[symbol] = stop_price
            self.stop_orders[symbol] = self.buy(
                data=data, exectype=bt.Order.Stop, price=stop_price
            )
            self.log(f"STOP LOSS SET for {symbol} at {stop_price:.5f}")

    def _set_profit_target(self, symbol):
        for data in self.datas:
            if data._name == symbol:
                break
        else:
            return
        atr_value = self.inds[symbol]["atr"][0]
        current_price = data.close[0]
        if self.trade_positions[symbol] > 0:  # Long
            target_price = current_price + (self.p.profit_target * atr_value)
            self.target_orders[symbol] = self.sell(
                data=data, exectype=bt.Order.Limit, price=target_price
            )
            self.log(f"PROFIT TARGET SET for {symbol} at {target_price:.5f}")
        elif self.trade_positions[symbol] < 0:  # Short
            target_price = current_price - (self.p.profit_target * atr_value)
            self.target_orders[symbol] = self.buy(
                data=data, exectype=bt.Order.Limit, price=target_price
            )
            self.log(f"PROFIT TARGET SET for {symbol} at {target_price:.5f}")

    def _update_trailing_stop(self, symbol):
        for data in self.datas:
            if data._name == symbol:
                break
        else:
            return
        atr_value = self.inds[symbol]["atr"][0]
        current_price = data.close[0]
        if self.trade_positions[symbol] > 0:  # Long
            new_stop = current_price - (self.p.atr_multiplier * atr_value)
            if new_stop > self.stop_prices[symbol]:
                if self.stop_orders[symbol] is not None:
                    self.cancel(self.stop_orders[symbol])
                    self.stop_orders[symbol] = None
                self.stop_prices[symbol] = new_stop
                self.stop_orders[symbol] = self.sell(
                    data=data, exectype=bt.Order.Stop, price=new_stop
                )
                self.log(f"TRAILING STOP UPDATED for {symbol} to {new_stop:.5f}")
        elif self.trade_positions[symbol] < 0:  # Short
            new_stop = current_price + (self.p.atr_multiplier * atr_value)
            if new_stop < self.stop_prices[symbol]:
                if self.stop_orders[symbol] is not None:
                    self.cancel(self.stop_orders[symbol])
                    self.stop_orders[symbol] = None
                self.stop_prices[symbol] = new_stop
                self.stop_orders[symbol] = self.buy(
                    data=data, exectype=bt.Order.Stop, price=new_stop
                )
                self.log(f"TRAILING STOP UPDATED for {symbol} to {new_stop:.5f}")

    def _is_in_session(self, data):
        if not self.p.use_time_filter:
            return True
        current_time = bt.num2date(data.datetime[0])
        hour = current_time.hour
        return self.p.session_start <= hour < self.p.session_end

    def next(self):
        for i, data in enumerate(self.datas):
            symbol = data._name
            pos = self.trade_positions[symbol]
            inds = self.inds[symbol]
            if self.orders[symbol] is not None:
                continue
            if pos != 0 and self.p.trail_stop:
                self._update_trailing_stop(symbol)
            if not self._is_in_session(data):
                if pos != 0 and data.datetime.time().hour >= self.p.session_end - 1:
                    self.log(f"SESSION END: Closing position for {symbol}")
                    self.close(data=data)
                    self.trade_positions[symbol] = 0
                continue

            fast_ema = inds["fast_ema"][0]
            slow_ema = inds["slow_ema"][0]
            macd = inds["macd"][0]
            signal = inds["signal"][0]
            macd_hist = inds["macd_hist"][0]
            rsi = inds["rsi"][0]
            momentum = inds["momentum"][0]
            boll_mid = inds["bollinger"].mid[0]
            prev_macd_hist = inds["macd_hist"][-1]

            if pos == 0:
                if (
                    fast_ema > slow_ema
                    and macd > signal
                    and macd_hist > 0
                    and prev_macd_hist <= 0
                    and rsi > 50
                    and momentum > 0
                    and data.close[0] > boll_mid
                ):
                    self.log(f"BUY SIGNAL for {symbol} at {data.close[0]:.5f}")
                    self.orders[symbol] = self.buy(data=data)
                elif (
                    fast_ema < slow_ema
                    and macd < signal
                    and macd_hist < 0
                    and prev_macd_hist >= 0
                    and rsi < 50
                    and momentum < 0
                    and data.close[0] < boll_mid
                ):
                    self.log(f"SELL SIGNAL for {symbol} at {data.close[0]:.5f}")
                    self.orders[symbol] = self.sell(data=data)
            elif pos > 0:
                if (macd < signal and macd_hist < 0 and prev_macd_hist >= 0) or fast_ema < slow_ema:
                    self.log(f"CLOSE LONG for {symbol} at {data.close[0]:.5f}")
                    if self.stop_orders[symbol] is not None:
                        self.cancel(self.stop_orders[symbol])
                        self.stop_orders[symbol] = None
                    if self.target_orders[symbol] is not None:
                        self.cancel(self.target_orders[symbol])
                        self.target_orders[symbol] = None
                    self.close(data=data)
                    self.trade_positions[symbol] = 0
            elif pos < 0:
                if (macd > signal and macd_hist > 0 and prev_macd_hist <= 0) or fast_ema > slow_ema:
                    self.log(f"CLOSE SHORT for {symbol} at {data.close[0]:.5f}")
                    if self.stop_orders[symbol] is not None:
                        self.cancel(self.stop_orders[symbol])
                        self.stop_orders[symbol] = None
                    if self.target_orders[symbol] is not None:
                        self.cancel(self.target_orders[symbol])
                        self.target_orders[symbol] = None
                    self.close(data=data)
                    self.trade_positions[symbol] = 0

    def stop(self):
        self.log("Backtest completed")
        portfolio_value = self.broker.getvalue()
        initial_value = self.broker.startingcash
        profit_pct = (portfolio_value / initial_value - 1.0) * 100
        self.log(f"Final Portfolio Value: {portfolio_value:.2f}")
        self.log(f"Profit/Loss: {profit_pct:.2f}%")