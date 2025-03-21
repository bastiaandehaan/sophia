#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backtrader adapter voor Sophia Trading Framework.
Converteert MT5 data naar Backtrader formaat en biedt interfaces voor backtesting.
"""

import datetime
import logging
from typing import Dict, List, Optional, Union, Tuple, Any

import MetaTrader5 as mt5
import backtrader as bt
import pandas as pd

from src.connector import MT5Connector


class MT5DataFeed(bt.feeds.PandasData):
    """
    Aangepaste Backtrader datafeed voor MT5 OHLCV data.
    """

    params = (
        ("datetime", "time"),
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "tick_volume"),
        ("openinterest", None),
    )


class BacktraderAdapter:
    """
    Adapter die MT5 data converteert naar Backtrader formaat en backtests faciliteert.
    """

    def __init__(
            self, config: Dict[str, Any] = None,
            connector: Optional[MT5Connector] = None
    ):
        """
        Initialiseer de Backtrader adapter.

        Args:
            config: Configuratie dictionary voor de adapter
            connector: Optionele MT5Connector instantie, wordt aangemaakt indien None
        """
        self.logger = logging.getLogger("sophia.backtrader")
        self.config = config or {}

        # Intern geheugen voor data caching
        self.data_cache = {}

        # Connector voor MT5 data
        if connector:
            self.connector = connector
        else:
            from src.utils import load_config

            mt5_config = config.get("mt5", load_config().get("mt5", {}))
            self.connector = MT5Connector(mt5_config)

        # Cerebro instantie
        self.cerebro = None

        # Beschikbare timeframes mapping
        self.timeframe_map = {
            "M1": (bt.TimeFrame.Minutes, 1),
            "M5": (bt.TimeFrame.Minutes, 5),
            "M15": (bt.TimeFrame.Minutes, 15),
            "M30": (bt.TimeFrame.Minutes, 30),
            "H1": (bt.TimeFrame.Minutes, 60),
            "H4": (bt.TimeFrame.Minutes, 240),
            "D1": (bt.TimeFrame.Days, 1),
            "W1": (bt.TimeFrame.Weeks, 1),
            "MN1": (bt.TimeFrame.Months, 1),
        }

    def get_historical_data(
            self,
            symbol: str,
            timeframe: str,
            from_date: Union[str, datetime.datetime],
            to_date: Union[str, datetime.datetime] = None,
            include_current_candle: bool = False,
    ) -> pd.DataFrame:
        """
        Haal historische data op van MT5 en converteer naar pandas DataFrame.

        Args:
            symbol: Handelssymbool (bijv. "EURUSD")
            timeframe: Timeframe als string (bijv. "M1", "H1", "D1")
            from_date: Startdatum als string ('YYYY-MM-DD') of datetime
            to_date: Einddatum (standaard: nu)
            include_current_candle: Of de huidige, onvoltooide candle meegenomen moet worden

        Returns:
            DataFrame met OHLCV data
        """
        # Converteer string datums naar datetime objecten
        if isinstance(from_date, str):
            from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d")

        if isinstance(to_date, str):
            to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d")
        elif to_date is None:
            to_date = datetime.datetime.now()

        # Cache key voor het hergebruiken van data
        cache_key = f"{symbol}_{timeframe}_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}"

        # Controleer of we al data in de cache hebben
        if cache_key in self.data_cache:
            self.logger.info(f"Returning cached data for {cache_key}")
            return self.data_cache[cache_key]

        # Zorg dat we verbonden zijn met MT5
        if not self.connector.connected:
            self.connector.connect()

        # Verkrijg de juiste MT5 timeframe constante
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }

        mt5_timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_D1)

        # Haal data op van MT5
        self.logger.info(
            f"Fetching {symbol} {timeframe} data from {from_date} to {to_date}"
        )
        rates = mt5.copy_rates_range(symbol, mt5_timeframe, from_date, to_date)

        if rates is None or len(rates) == 0:
            self.logger.error(f"No data received for {symbol} {timeframe}")
            return pd.DataFrame()

        # Converteer naar DataFrame
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")

        # Verwijder de huidige, onvoltooide candle indien nodig
        if not include_current_candle and len(df) > 0:
            current_time = datetime.datetime.now()
            if timeframe in ["M1", "M5", "M15", "M30", "H1", "H4"]:
                df = df[
                    df["time"]
                    < current_time.replace(
                        microsecond=0, second=0, minute=current_time.minute
                    )
                    ]
            elif timeframe == "D1":
                df = df[
                    df["time"]
                    < current_time.replace(microsecond=0, second=0, minute=0,
                                           hour=0)
                    ]

        # Cache de data voor toekomstig gebruik
        self.data_cache[cache_key] = df

        self.logger.info(f"Retrieved {len(df)} bars for {symbol} {timeframe}")
        return df

    def prepare_cerebro(self, initial_cash: float = 10000.0) -> bt.Cerebro:
        """
        Maak en configureer een nieuwe Backtrader Cerebro instantie.

        Args:
            initial_cash: Startkapitaal voor de backtest

        Returns:
            Geconfigureerde Cerebro instantie
        """
        cerebro = bt.Cerebro()
        cerebro.broker.set_cash(initial_cash)

        # Commissie instellen (standaard 0.0001 = 1 pip voor forex)
        commission = self.config.get("commission", 0.0001)
        cerebro.broker.setcommission(commission=commission)

        # Sizers toevoegen
        # Standaard: percentage van kapitaal (vergelijkbaar met Sophia risico module)
        default_risk = 0.01  # 1% risico per trade
        cerebro.addsizer(bt.sizers.PercentSizer, percents=default_risk * 100)

        # Analyzers voor performance metrics
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe",
                            riskfreerate=0.0)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

        self.cerebro = cerebro
        return cerebro

    def add_data(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        """
        Voeg data toe aan de Cerebro instantie.

        Args:
            df: DataFrame met OHLCV data
            symbol: Symbool voor de data
            timeframe: Timeframe als string
        """
        if self.cerebro is None:
            self.prepare_cerebro()

        # Converteer pandas DataFrame naar Backtrader data feed
        data_feed = MT5DataFeed(
            dataname=df,
            name=symbol,
            timeframe=self.timeframe_map.get(timeframe, (bt.TimeFrame.Days, 1))[
                0],
            compression=
            self.timeframe_map.get(timeframe, (bt.TimeFrame.Days, 1))[1],
        )

        self.cerebro.adddata(data_feed, name=symbol)
        self.logger.info(f"Added {symbol} {timeframe} data to cerebro")

    def add_strategy(self, strategy_class, **kwargs) -> None:
        """
        Voeg een strategie toe aan Cerebro met de gegeven parameters.

        Args:
            strategy_class: Backtrader Strategy class
            **kwargs: Parameters voor de strategie
        """
        if self.cerebro is None:
            self.prepare_cerebro()

        self.cerebro.addstrategy(strategy_class, **kwargs)
        self.logger.info(
            f"Added strategy {strategy_class.__name__} with params: {kwargs}"
        )

    def run_backtest(self) -> Tuple[List, Dict[str, Any]]:
        """
        Voer de backtest uit en retourneer resultaten.

        Returns:
            Tuple van (resultaten, metrics)
        """
        if self.cerebro is None:
            raise ValueError(
                "No cerebro instance available. Call prepare_cerebro first."
            )

        self.logger.info("Starting backtest...")
        results = self.cerebro.run()

        # Verzamel metrics van analyzers
        metrics = {}
        if results and len(results) > 0:
            strat = results[0]

            # Sharpe ratio
            sharpe = strat.analyzers.sharpe.get_analysis()
            metrics["sharpe_ratio"] = sharpe.get("sharperatio", 0.0)

            # Drawdown
            dd = strat.analyzers.drawdown.get_analysis()
            metrics["max_drawdown_pct"] = dd.get("max", {}).get("drawdown", 0.0)
            metrics["max_drawdown_len"] = dd.get("max", {}).get("len", 0)

            # Trades
            trades = strat.analyzers.trades.get_analysis()
            metrics["total_trades"] = trades.get("total", {}).get("total", 0)
            metrics["won_trades"] = trades.get("won", {}).get("total", 0)
            metrics["lost_trades"] = trades.get("lost", {}).get("total", 0)

            if metrics["total_trades"] > 0:
                metrics["win_rate"] = (
                        metrics["won_trades"] / metrics["total_trades"] * 100
                )
            else:
                metrics["win_rate"] = 0.0

            # Returns
            returns = strat.analyzers.returns.get_analysis()
            metrics["annual_return"] = returns.get("ravg", 0.0) * 100
            metrics["total_return_pct"] = returns.get("rtot", 0.0) * 100

            # Final portfolio value
            metrics["final_value"] = self.cerebro.broker.getvalue()
            metrics["profit_factor"] = self._calculate_profit_factor(strat)

            self.logger.info(
                f"Backtest completed with final value: {metrics['final_value']:.2f}"
            )

        return results, metrics

    def plot_results(self, filename: str = None, **kwargs) -> None:
        """
        Plot de backtest resultaten.

        Args:
            filename: Bestandsnaam om de plot op te slaan (optioneel)
            **kwargs: Extra parameters voor de plot functie
        """
        if self.cerebro is None:
            raise ValueError(
                "No cerebro instance available. Run backtest first.")

        plot_args = {
            "style": "candle",
            "barup": "#2ecc71",  # Groene candles
            "bardown": "#e74c3c",  # Rode candles
            "volup": "#2ecc71",
            "voldown": "#e74c3c",
            "grid": True,
            "subplot": True,
            "volume": True,
        }

        # Update met eventuele custom parameters
        plot_args.update(kwargs)

        if filename:
            self.cerebro.plot(**plot_args,
                              savefig=dict(fname=filename, dpi=300))
            self.logger.info(f"Plot saved to {filename}")
        else:
            self.cerebro.plot(**plot_args)

    def _calculate_profit_factor(self, strategy) -> float:
        """
        Bereken de profit factor (bruto winst / bruto verlies).

        Args:
            strategy: Backtrader strategie instantie

        Returns:
            Profit factor als float
        """
        trades = strategy.analyzers.trades.get_analysis()

        # Haal winst en verlies bedragen op
        won_total = trades.get("won", {}).get("pnl", 0.0)
        lost_total = abs(trades.get("lost", {}).get("pnl", 0.0))

        if lost_total == 0:
            return float("inf") if won_total > 0 else 0.0

        return won_total / lost_total
