 src/backtest.py
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import backtrader as bt
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple, Type

# Zorg dat de Sophia modules beschikbaar zijn
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.strategy import TurtleStrategy
from src.utils import setup_logging, load_config

# Logger instellen
logger = setup_logging()


class TurtleStrategyBT(bt.Strategy):
    """
    Backtrader-implementatie van de Turtle Trading strategie.
    """
    params = (('entry_period', 20),  # Donchian channel periode voor entry
              ('exit_period', 10),  # Donchian channel periode voor exit
              ('atr_period', 14),  # ATR periode
              ('risk_percent', 0.01),  # Risico per trade als percentage van account
              ('use_vol_filter', True), ('vol_lookback', 100), ('vol_threshold', 1.2),)

    def __init__(self):
        """Initialize de Backtrader Turtle strategie."""
        self.entry_high = bt.indicators.Highest(self.data.high,
                                                period=self.p.entry_period)
        self.entry_low = bt.indicators.Lowest(self.data.low, period=self.p.entry_period)

        self.exit_high = bt.indicators.Highest(self.data.high,
                                               period=self.p.exit_period)
        self.exit_low = bt.indicators.Lowest(self.data.low, period=self.p.exit_period)

        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)

        # Volatiliteitsfilter
        if self.p.use_vol_filter:
            self.vol_ma = bt.indicators.SMA(self.atr, period=self.p.vol_lookback)

        # Handelsstatus bijhouden
        self.order = None
        self.entry_price = None
        self.stop_loss = None
        self.position_size = None

    def log(self, txt: str, dt=None):
        """Logging functie voor de strategie."""
        dt = dt or self.datas[0].datetime.date(0)
        logger.info(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """Verwerk order notificaties."""
        if order.status in [order.Submitted, order.Accepted]:
            # Order ingediend/geaccepteerd - Geen actie nodig
            return

        # Controleer of order is uitgevoerd
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.5f}, Size: {order.executed.size:.2f}')
            else:
                self.log(
                    f'SELL EXECUTED, Price: {order.executed.price:.5f}, Size: {order.executed.size:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Geannuleerd/Margin/Geweigerd')

        # Reset order referentie
        self.order = None

    def notify_trade(self, trade):
        """Verwerk trade notificaties."""
        if not trade.isclosed:
            return

        self.log(f'TRADE P/L: Bruto {trade.pnl:.2f}, Netto {trade.pnlcomm:.2f}')

    def next(self):
        """Voer strategie uit voor de volgende bar."""
        # Als er een openstaande order is, doe niets
        if self.order:
            return

        # Volatiliteitsfilter controleren
        vol_filter_passed = True
        if self.p.use_vol_filter and len(self.vol_ma) > 0:
            vol_filter_passed = self.atr[0] > (self.vol_ma[0] * self.p.vol_threshold)

        # ENTRY LOGICA
        if not self.position:  # We hebben geen positie
            if vol_filter_passed:
                # Long entry (breakout boven entry_high)
                if self.data.close[0] > self.entry_high[-1]:
                    # Bereken positiegrootte
                    price = self.data.close[0]
                    stop_price = price - (2 * self.atr[0])
                    risk_per_share = price - stop_price

                    # Bereken aantal aandelen op basis van risicopercentage
                    risk_amount = self.broker.getvalue() * self.p.risk_percent
                    size = risk_amount / risk_per_share

                    # Rond af naar beneden voor consistentie
                    size = int(size)
                    if size <= 0:
                        size = 1  # Minimaal 1 aandeel

                    self.log(
                        f'BUY CREATE, Price: {price:.5f}, Size: {size}, Stop: {stop_price:.5f}')
                    self.order = self.buy(size=size)

                    # Sla entry en stop details op
                    self.entry_price = price
                    self.stop_loss = stop_price
                    self.position_size = size

                # Short entry (breakout onder entry_low)
                elif self.data.close[0] < self.entry_low[-1]:
                    # Bereken positiegrootte
                    price = self.data.close[0]
                    stop_price = price + (2 * self.atr[0])
                    risk_per_share = stop_price - price

                    # Bereken aantal aandelen op basis van risicopercentage
                    risk_amount = self.broker.getvalue() * self.p.risk_percent
                    size = risk_amount / risk_per_share

                    # Rond af naar beneden voor consistentie
                    size = int(size)
                    if size <= 0:
                        size = 1  # Minimaal 1 aandeel

                    self.log(
                        f'SELL CREATE, Price: {price:.5f}, Size: {size}, Stop: {stop_price:.5f}')
                    self.order = self.sell(size=size)

                    # Sla entry en stop details op
                    self.entry_price = price
                    self.stop_loss = stop_price
                    self.position_size = size

        # EXIT LOGICA
        else:  # We hebben een positie
            if self.position.size > 0:  # Long positie
                # Exit als prijs onder exit_low daalt
                if self.data.close[0] < self.exit_low[-1]:
                    self.log(f'CLOSE LONG, Price: {self.data.close[0]:.5f}')
                    self.order = self.close()
            else:  # Short positie
                # Exit als prijs boven exit_high stijgt
                if self.data.close[0] > self.exit_high[-1]:
                    self.log(f'CLOSE SHORT, Price: {self.data.close[0]:.5f}')
                    self.order = self.close()


class REMAStrategy(bt.Strategy):
    """
    Responsive Exponential Moving Average (REMA) strategie.

    Deze strategie gebruikt twee EMA's: een snelle en een langzame.
    - Koopt wanneer de snelle EMA de langzame EMA kruist van beneden naar boven
    - Verkoopt wanneer de snelle EMA de langzame EMA kruist van boven naar beneden
    - Bevat een ADX filter om te zorgen dat we alleen in trendende markten handelen
    - Optimaliseert posities met ATR-gebaseerd risicomanagement
    """
    params = (('fast_ema', 8),  # Snelle EMA periode
              ('slow_ema', 21),  # Langzame EMA periode
              ('adx_period', 14),  # ADX periode
              ('adx_threshold', 25),  # Minimale ADX waarde voor trades
              ('atr_period', 14),  # ATR periode voor stop loss
              ('atr_multiplier', 2),  # Vermenigvuldiger voor ATR stop loss
              ('risk_percent', 0.01),  # Risico per trade als percentage van account
              ('use_trailing_stop', True),  # Gebruik trailing stop loss
    )

    def __init__(self):
        """Initialize de REMA strategie."""
        # Kernindicatoren
        self.fast_ema = bt.indicators.EMA(self.data.close, period=self.p.fast_ema)
        self.slow_ema = bt.indicators.EMA(self.data.close, period=self.p.slow_ema)

        # Crossovers detecteren
        self.crossover = bt.indicators.CrossOver(self.fast_ema, self.slow_ema)

        # ADX voor trendsterkte
        self.adx = bt.indicators.ADX(self.data, period=self.p.adx_period)

        # ATR voor stop loss berekening
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)

        # Trailing stop variabelen
        self.trailing_stop = None

        # Handelsstatus bijhouden
        self.order = None

    def log(self, txt: str, dt=None):
        """Logging functie voor de strategie."""
        dt = dt or self.datas[0].datetime.date(0)
        logger.info(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """Verwerk order notificaties."""
        if order.status in [order.Submitted, order.Accepted]:
            # Order ingediend/geaccepteerd - Geen actie nodig
            return

        # Controleer of order is uitgevoerd
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.5f}, Size: {order.executed.size:.2f}')
                # Stel trailing stop in voor long positie
                if self.p.use_trailing_stop:
                    self.trailing_stop = order.executed.price - (
                                self.atr[0] * self.p.atr_multiplier)
            else:
                self.log(
                    f'SELL EXECUTED, Price: {order.executed.price:.5f}, Size: {order.executed.size:.2f}')
                # Stel trailing stop in voor short positie
                if self.p.use_trailing_stop:
                    self.trailing_stop = order.executed.price + (
                                self.atr[0] * self.p.atr_multiplier)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Geannuleerd/Margin/Geweigerd')

        # Reset order referentie
        self.order = None

    def notify_trade(self, trade):
        """Verwerk trade notificaties."""
        if not trade.isclosed:
            return

        self.log(f'TRADE P/L: Bruto {trade.pnl:.2f}, Netto {trade.pnlcomm:.2f}')
        # Reset trailing stop na het sluiten van een trade
        self.trailing_stop = None

    def next(self):
        """Voer strategie uit voor de volgende bar."""
        # Als er een openstaande order is, doe niets
        if self.order:
            return

        # Controleer op trailing stop
        if self.p.use_trailing_stop and self.trailing_stop is not None and self.position:
            if self.position.size > 0:  # Long positie
                # Update trailing stop naar boven als prijs stijgt
                if self.data.close[0] - (
                        self.atr[0] * self.p.atr_multiplier) > self.trailing_stop:
                    self.trailing_stop = self.data.close[0] - (
                                self.atr[0] * self.p.atr_multiplier)

                # Sluit positie als prijs onder trailing stop zakt
                if self.data.close[0] < self.trailing_stop:
                    self.log(
                        f'TRAILING STOP HIT, Close: {self.data.close[0]:.5f}, Stop: {self.trailing_stop:.5f}')
                    self.order = self.close()
                    return

            else:  # Short positie
                # Update trailing stop naar beneden als prijs daalt
                if self.data.close[0] + (
                        self.atr[0] * self.p.atr_multiplier) < self.trailing_stop:
                    self.trailing_stop = self.data.close[0] + (
                                self.atr[0] * self.p.atr_multiplier)

                # Sluit positie als prijs boven trailing stop stijgt
                if self.data.close[0] > self.trailing_stop:
                    self.log(
                        f'TRAILING STOP HIT, Close: {self.data.close[0]:.5f}, Stop: {self.trailing_stop:.5f}')
                    self.order = self.close()
                    return

        # ADX filter, alleen handelen als ADX boven threshold ligt
        if self.adx < self.p.adx_threshold:
            return

        # SIGNALEN VERWERKEN
        if not self.position:  # We hebben geen positie
            # Buy signaal: fast EMA kruist slow EMA van onder naar boven
            if self.crossover > 0:
                # Bereken positiegrootte
                price = self.data.close[0]
                stop_price = price - (self.atr[0] * self.p.atr_multiplier)
                risk_per_share = price - stop_price

                # Bereken aantal aandelen op basis van risicopercentage
                risk_amount = self.broker.getvalue() * self.p.risk_percent
                size = risk_amount / risk_per_share

                # Rond af naar beneden voor consistentie
                size = int(size)
                if size <= 0:
                    size = 1  # Minimaal 1 aandeel

                self.log(
                    f'BUY CREATE, Price: {price:.5f}, Size: {size}, Stop: {stop_price:.5f}')
                self.order = self.buy(size=size)

            # Sell signaal: fast EMA kruist slow EMA van boven naar onder
            elif self.crossover < 0:
                # Bereken positiegrootte
                price = self.data.close[0]
                stop_price = price + (self.atr[0] * self.p.atr_multiplier)
                risk_per_share = stop_price - price

                # Bereken aantal aandelen op basis van risicopercentage
                risk_amount = self.broker.getvalue() * self.p.risk_percent
                size = risk_amount / risk_per_share

                # Rond af naar beneden voor consistentie
                size = int(size)
                if size <= 0:
                    size = 1  # Minimaal 1 aandeel

                self.log(
                    f'SELL CREATE, Price: {price:.5f}, Size: {size}, Stop: {stop_price:.5f}')
                self.order = self.sell(size=size)

        else:  # We hebben een positie
            # Verkoop signaal en we hebben een long positie
            if self.crossover < 0 and self.position.size > 0:
                self.log(f'CLOSE LONG, Price: {self.data.close[0]:.5f}')
                self.order = self.close()

            # Koop signaal en we hebben een short positie
            elif self.crossover > 0 and self.position.size < 0:
                self.log(f'CLOSE SHORT, Price: {self.data.close[0]:.5f}')
                self.order = self.close()


class SophiaBacktest:
    """
    Backtest manager voor Sophia trading strategies.
    """

    def __init__(self, config: Dict[str, Any] = None, config_path: str = None):
        """
        Initialiseer de backtest manager.

        Args:
            config: Config dictionary (optioneel)
            config_path: Pad naar config file (optioneel)
        """
        self.logger = logger

        # Laad config
        if config is not None:
            self.config = config
        elif config_path is not None:
            self.config = load_config(config_path)
        else:
            # Default config pad
            config_path = os.path.join(project_root, "config", "settings.json")
            self.config = load_config(config_path)

        # Initialiseer de backtrader engine
        self.cerebro = bt.Cerebro()

        # Stel standaard broker parameters in
        self.cerebro.broker.setcash(100000.0)  # Startkapitaal
        self.cerebro.broker.setcommission(commission=0.001)  # 0.1% commissie

        # Optimalisatieresultaten
        self.optimization_results = None

    def _prepare_data(self, data_path: str, symbol: str, start_date: str = None,
                      end_date: str = None,
                      timeframe: str = None) -> bt.feeds.PandasData:
        """
        Bereid data voor om in Backtrader te gebruiken.

        Args:
            data_path: Pad naar CSV of dataframe
            symbol: Handelssymbool
            start_date: Start datum in 'YYYY-MM-DD' format
            end_date: Eind datum in 'YYYY-MM-DD' format
            timeframe: Tijdsframe voor de data ('M1', 'H1', 'D1', etc.)

        Returns:
            bt.feeds.PandasData object
        """
        # Converteer datums naar datetime als ze zijn gegeven
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        if isinstance(data_path, pd.DataFrame):
            # Als een dataframe wordt doorgegeven
            df = data_path
        elif data_path.endswith('.csv'):
            # Laad data van CSV bestand
            df = pd.read_csv(data_path)

            # Converteer datum kolom
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
                df.set_index('time', inplace=True)
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)

        else:
            raise ValueError(f"Niet-ondersteund data format: {data_path}")

        # Zorg dat we hebben: open, high, low, close, volume
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns and col.capitalize() not in df.columns:
                self.logger.warning(
                    f"Kolom '{col}' ontbreekt in data, wordt toegevoegd met default waarden")
                if col == 'volume':
                    df[col] = 1000  # Default volume
                else:
                    # Gebruik close waarden voor ontbrekende prijzen
                    close_col = 'close' if 'close' in df.columns else 'Close'
                    df[col] = df[close_col]

        # Standaardiseer kolomnamen naar lowercase
        df.columns = [col.lower() for col in df.columns]

        # Filter op datum als nodig
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        # Maak een Backtrader data feed
        data = bt.feeds.PandasData(dataname=df, name=symbol)

        return data

    def add_data(self, data_path: Union[str, pd.DataFrame], symbol: str,
                 start_date: str = None, end_date: str = None, timeframe: str = None):
        """
        Voeg data toe aan de backtest.

        Args:
            data_path: Pad naar CSV of dataframe
            symbol: Handelssymbool
            start_date: Start datum in 'YYYY-MM-DD' format
            end_date: Eind datum in 'YYYY-MM-DD' format
            timeframe: Tijdsframe voor de data
        """
        # Bereid data voor
        data = self._prepare_data(data_path, symbol, start_date, end_date, timeframe)

        # Voeg data toe aan cerebro
        self.cerebro.adddata(data)
        self.logger.info(f"Data toegevoegd voor {symbol}")

    def add_strategy(self, strategy_name: str = "turtle",
                     strategy_params: Dict[str, Any] = None):
        """
        Voeg een strategie toe aan de backtest.

        Args:
            strategy_name: "turtle" of "rema"
            strategy_params: Parameters voor de strategie
        """
        # Default parameters als geen worden opgegeven
        if strategy_params is None:
            strategy_params = {}

        # Voeg de juiste strategie toe
        if strategy_name.lower() == "turtle":
            # Stel standaard parameters in van de config als beschikbaar
            if 'strategy' in self.config:
                for key, value in self.config['strategy'].items():
                    if key in ['entry_period', 'exit_period', 'atr_period',
                               'vol_filter', 'vol_lookback',
                               'vol_threshold'] and key not in strategy_params:
                        strategy_params[key] = value

            # Risico percentage toevoegen als niet opgegeven
            if 'risk_percent' not in strategy_params and 'risk' in self.config:
                strategy_params['risk_percent'] = self.config['risk'].get(
                    'risk_per_trade', 0.01)

            self.cerebro.addstrategy(TurtleStrategyBT, **strategy_params)
            self.logger.info(
                f"Turtle strategie toegevoegd met parameters: {strategy_params}")

        elif strategy_name.lower() == "rema":
            # Risico percentage toevoegen als niet opgegeven
            if 'risk_percent' not in strategy_params and 'risk' in self.config:
                strategy_params['risk_percent'] = self.config['risk'].get(
                    'risk_per_trade', 0.01)

            self.cerebro.addstrategy(REMAStrategy, **strategy_params)
            self.logger.info(
                f"REMA strategie toegevoegd met parameters: {strategy_params}")

        else:
            raise ValueError(
                f"Onbekende strategie: {strategy_name}. Kies 'turtle' of 'rema'.")

    def optimize_strategy(self, strategy_name: str, param_grid: Dict[str, List[Any]],
                          metric: str = 'sharpe'):
        """
        Optimaliseer strategie parameters met grid search.

        Args:
            strategy_name: "turtle" of "rema"
            param_grid: Dictionary met parameter namen en waarden om te testen
            metric: Optimalisatie metric ('sharpe', 'returns', 'drawdown')
        """
        self.logger.info(
            f"Optimaliseer {strategy_name} strategie met grid: {param_grid}")

        # Zet cerebro op voor optimalisatie
        self.cerebro = bt.Cerebro(optreturn=True)
        self.cerebro.broker.setcash(100000.0)
        self.cerebro.broker.setcommission(commission=0.001)

        # Voeg analyzers toe
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

        # Kies de juiste strategie klasse
        strategy_class = TurtleStrategyBT if strategy_name.lower() == 'turtle' else REMAStrategy

        # Voeg strategie toe met parameters voor optimalisatie
        self.cerebro.optstrategy(strategy_class, **param_grid)

        # Voer optimalisatie uit
        results = self.cerebro.run()
        self.logger.info(f"Optimalisatie voltooid, {len(results)} combinaties getest")

        # Verzamel resultaten
        opt_results = []

        for run in results:
            params = run[0].params
            sharpe = run[0].analyzers.sharpe.get_analysis().get('sharperatio', 0.0)
            returns = run[0].analyzers.returns.get_analysis().get('rtot', 0.0)
            drawdown = run[0].analyzers.drawdown.get_analysis().get('max', {}).get(
                'drawdown', 0.0)

            # Parameters uitlezen
            param_values = {}
            for param_name in param_grid.keys():
                param_values[param_name] = getattr(params, param_name)

            # Resultaat toevoegen
            opt_results.append(
                {'params': param_values, 'sharpe': sharpe if sharpe else 0.0,
                    'returns': returns if returns else 0.0,
                    'drawdown': drawdown if drawdown else 0.0})

        # Sorteer op gekozen metric
        if metric == 'sharpe':
            opt_results.sort(key=lambda x: x['sharpe'], reverse=True)
        elif metric == 'returns':
            opt_results.sort(key=lambda x: x['returns'], reverse=True)
        elif metric == 'drawdown':
            opt_results.sort(key=lambda x: x['drawdown'],
                             reverse=False)  # Kleinere drawdown is beter

        # Sla resultaten op
        self.optimization_results = opt_results

        # Log beste resultaat
        if opt_results:
            best = opt_results[0]
            self.logger.info(f"Beste parameters gevonden: {best['params']}")
            self.logger.info(
                f"Sharpe Ratio: {best['sharpe']:.4f}, Returns: {best['returns']:.2%}, Max Drawdown: {best['drawdown']:.2%}")

        # Reset cerebro na optimalisatie
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(100000.0)
        self.cerebro.broker.setcommission(commission=0.001)

        return opt_results

    def run(self, plot: bool = True) -> Dict[str, Any]:
        """
        Voer de backtest uit.

        Args:
            plot: Of visualisatie gemaakt moet worden

        Returns:
            Dict met backtest resultaten
        """
        self.logger.info("Start backtest uitvoering")

        # Voeg analysers toe
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

        # Standaardwaarden
        self.cerebro.addsizer(bt.sizers.PercentSizer, percents=10)

        # Voer backtest uit
        results = self.cerebro.run()
        result = results[0]  # Eerste strategie

        # Verzamel resultaten
        sharpe = result.analyzers.sharpe.get_analysis().get('sharperatio', 0.0)
        returns = result.analyzers.returns.get_analysis().get('rtot', 0.0)
        drawdown = result.analyzers.drawdown.get_analysis().get('max', {}).get(
            'drawdown', 0.0)

        trades_analysis = result.analyzers.trades.get_analysis()
        total_trades = trades_analysis.get('total', {}).get('total', 0)
        win_trades = trades_analysis.get('won', {}).get('total', 0)
        loss_trades = trades_analysis.get('lost', {}).get('total', 0)

        win_rate = win_trades / total_trades if total_trades > 0 else 0.0

        final_value = self.cerebro.broker.getvalue()
        starting_value = self.cerebro.broker.startingcash
        profit_perc = (final_value / starting_value - 1.0) * 100

        # Resultaten tonen
        self.logger.info(f"Backtest resultaten:")
        self.logger.info(
            f"Eindvermogen: ${final_value:.2f} (Start: ${starting_value:.2f})")
        self.logger.info(
            f"Netto winst: ${final_value - starting_value:.2f} ({profit_perc:.2f}%)")
        self.logger.info(f"Sharpe Ratio: {sharpe:.4f}")
        self.logger.info(f"Maximale drawdown: {drawdown:.2%}")
        self.logger.info(
            f"Totaal trades: {total_trades} (Win: {win_trades}, Verlies: {loss_trades})")
        self.logger.info(f"Win rate: {win_rate:.2%}")

        # Plot resultaten
        if plot:
            self.cerebro.plot(style='candle', barup='green', bardown='red',
                              volume=False, grid=True, plotdist=0.5)