#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Strategy Adapter Module voor Sophia Trading Framework.

Deze adapter zorgt voor de conversie tussen Sophia trading strategieën en
Backtrader compatibele strategie-implementaties. De adapter maakt het mogelijk
om bestaande Sophia strategieën te gebruiken in backtesting zonder aanpassingen
aan de originele code.
"""

import os
import sys
import logging
from typing import Dict, Any, Type, Optional, List, Tuple, Union
from datetime import datetime

# Zorg dat project root in sys.path staat
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import backtrader as bt
import pandas as pd
import numpy as np


class StrategyAdapter:
    """
    Adapter klasse die Sophia strategieën omzet naar Backtrader strategieën.

    Deze klasse biedt functionaliteit voor:
    1. Conversie van signalen tussen de twee systemen
    2. Parameter mapping tussen Sophia en Backtrader
    3. Performance metriek standaardisatie
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialiseer de strategy adapter.

        Args:
            logger: Optionele logger instantie
        """
        self.logger = logger or logging.getLogger("sophia.strategy_adapter")

    def adapt_turtle_strategy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converteer Sophia Turtle strategie parameters naar Backtrader formaat.

        Args:
            params: Sophia strategie parameters

        Returns:
            Dict met Backtrader compatibele parameters
        """
        # Map parameters naar Backtrader specifieke parameters
        bt_params = {
            'entry_period': params.get('entry_period', 20),
            'exit_period': params.get('exit_period', 10),
            'atr_period': params.get('atr_period', 14),
            'risk_pct': params.get('risk_per_trade', 0.01),
            'use_vol_filter': params.get('vol_filter', True),
            'vol_lookback': params.get('vol_lookback', 100),
            'vol_threshold': params.get('vol_threshold', 1.2),
            'trend_filter': params.get('use_trend_filter', True),
            'trend_period': params.get('trend_period', 200),
            'pyramiding': params.get('pyramiding', 1)
        }

        self.logger.debug(f"Adapted Turtle strategy parameters: {bt_params}")
        return bt_params

    def adapt_ema_strategy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converteer Sophia EMA strategie parameters naar Backtrader formaat.

        Args:
            params: Sophia strategie parameters

        Returns:
            Dict met Backtrader compatibele parameters
        """
        # Map parameters naar Backtrader specifieke parameters
        bt_params = {
            'fast_ema': params.get('fast_ema', 9),
            'slow_ema': params.get('slow_ema', 21),
            'signal_ema': params.get('signal_ema', 5),
            'rsi_period': params.get('rsi_period', 14),
            'rsi_upper': params.get('rsi_upper', 70),
            'rsi_lower': params.get('rsi_lower', 30),
            'atr_period': params.get('atr_period', 14),
            'atr_multiplier': params.get('atr_multiplier', 2.0),
            'risk_pct': params.get('risk_per_trade', 0.01),
            'trail_stop': params.get('use_trailing_stop', True),
            'profit_target': params.get('profit_target', 3.0)
        }

        self.logger.debug(f"Adapted EMA strategy parameters: {bt_params}")
        return bt_params

    def get_strategy_class(self, strategy_type: str) -> Type[bt.Strategy]:
        """
        Geef de juiste Backtrader Strategy class voor het gegeven strategie type.

        Args:
            strategy_type: Type strategie ('turtle' of 'ema')

        Returns:
            Backtrader Strategy klasse

        Raises:
            ValueError: Als strategie type niet wordt ondersteund
        """
        from src.analysis.strategies.turtle_bt import TurtleStrategy
        from src.analysis.strategies.ema_bt import EMAStrategy

        strategy_map = {
            'turtle': TurtleStrategy,
            'ema': EMAStrategy
        }

        if strategy_type.lower() not in strategy_map:
            raise ValueError(
                f"Strategie type '{strategy_type}' wordt niet ondersteund. "
                f"Ondersteunde types: {list(strategy_map.keys())}")

        return strategy_map[strategy_type.lower()]

    def convert_sophia_signal_to_backtrader(self,
                                            sophia_signal: Dict[str, Any]) -> \
    Tuple[str, Dict[str, Any]]:
        """
        Converteer een Sophia signaal naar Backtrader formaat.

        Args:
            sophia_signal: Signaal data van Sophia strategie

        Returns:
            Tuple van (signaal type, signaal metadata)
        """
        signal = sophia_signal.get('signal')
        meta = sophia_signal.get('meta', {})

        # Als er geen signaal is, retourneer None
        if not signal:
            return 'no_signal', {}

        # Map Sophia signalen naar Backtrader signalen
        signal_map = {
            'BUY': 'buy',
            'SELL': 'sell',
            'CLOSE_BUY': 'close',
            'CLOSE_SELL': 'close'
        }

        bt_signal = signal_map.get(signal, 'no_signal')

        # Metadata conversie
        bt_meta = {
            'price': meta.get('entry_price', 0),
            'stop_loss': meta.get('stop_loss', 0),
            'reason': meta.get('reason', 'unknown'),
        }

        return bt_signal, bt_meta

    def convert_backtest_results(self, bt_results: Dict[str, Any]) -> Dict[
        str, Any]:
        """
        Converteer Backtrader resultaten naar Sophia formaat voor consistente rapportage.

        Args:
            bt_results: Resultaten van een Backtrader backtest

        Returns:
            Dict met gestandaardiseerde resultaten
        """
        # Standaardiseer metrieken tussen beide systemen
        standard_results = {
            'net_profit': bt_results.get('total_return_pct', 0),
            'sharpe_ratio': bt_results.get('sharpe_ratio', 0),
            'max_drawdown': bt_results.get('max_drawdown_pct', 0),
            'win_rate': bt_results.get('win_rate', 0),
            'profit_factor': bt_results.get('profit_factor', 0),
            'total_trades': bt_results.get('total_trades', 0),
            'avg_trade': bt_results.get('avg_trade_pnl', 0),
            'trading_period': {
                'start': bt_results.get('start_date', ''),
                'end': bt_results.get('end_date', '')
            }
        }

        return standard_results

    def create_bt_data_feed(self, df: pd.DataFrame, symbol: str,
                            timeframe: str) -> bt.feeds.PandasData:
        """
        Creëer een Backtrader data feed van een pandas DataFrame.

        Args:
            df: DataFrame met OHLC data
            symbol: Symbool voor de data
            timeframe: Timeframe voor de data

        Returns:
            Backtrader DataFeed object
        """
        # Standaardiseer kolomnamen
        required_cols = {
            'datetime': 'time',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'tick_volume',
            'openinterest': None
        }

        # Controleer of alle benodigde kolommen aanwezig zijn
        for bt_col, sophia_col in required_cols.items():
            if sophia_col and sophia_col not in df.columns:
                raise ValueError(
                    f"Kolom '{sophia_col}' ontbreekt in de DataFrame, nodig voor {bt_col}")

        # Creëer een aangepaste DataFeed klasse
        class SophiaData(bt.feeds.PandasData):
            params = tuple((bt_col, sophia_col) for bt_col, sophia_col in
                           required_cols.items())

        # Converteer 'time' kolom naar datetime indien nodig
        if 'time' in df.columns and not pd.api.types.is_datetime64_any_dtype(
            df['time']):
            df['time'] = pd.to_datetime(df['time'])

        # Creëer en return de data feed
        data_feed = SophiaData(
            dataname=df,
            name=symbol,
        )

        return data_feed

    def apply_sophia_order_sizing(self, bt_strategy: bt.Strategy,
                                  sizing_params: Dict[str, Any]) -> None:
        """
        Pas Sophia risico management toe op een Backtrader strategie.

        Args:
            bt_strategy: Backtrader strategie instantie
            sizing_params: Parameters voor order sizing
        """
        # Implementeer order sizing logica
        risk_pct = sizing_params.get('risk_per_trade', 0.01)

        # Voeg custom sizer toe aan strategie
        class SophiaSizer(bt.Sizer):
            params = (
                ('risk_pct', risk_pct),
            )

            def _getsizing(self, comminfo, cash, data, isbuy):
                if isbuy:
                    return self.p.risk_pct
                else:
                    return self.p.risk_pct

        bt_strategy.sizer = SophiaSizer()