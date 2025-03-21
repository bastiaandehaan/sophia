#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backtest script voor het Sophia Trading Framework.
Biedt een flexibele interface voor het backtesten van trading strategieën.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

from tabulate import tabulate

# Zorg dat het project root path in sys.path zit voor imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.analysis.backtrader_adapter import BacktraderAdapter
from src.analysis.strategies.turtle_bt import TurtleStrategy
from src.analysis.strategies.ema_bt import EMAStrategy


def setup_logging():
    """Setup logging voor backtest script."""
    log_dir = os.path.join(project_root, "src", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir,
                            f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    # Configureer de logger
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        handlers=[logging.FileHandler(log_file),
                                  logging.StreamHandler()], )

    return logging.getLogger("sophia.backtest")


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Laad de configuratie uit een JSON bestand.

    Args:
        config_path: Pad naar configuratiebestand (optioneel)

    Returns:
        Dictionary met configuratie
    """
    if config_path is None:
        config_path = os.path.join(project_root, "config", "settings.json")

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def parse_arguments():
    """Parse commandline argumenten."""
    parser = argparse.ArgumentParser(
        description="Sophia Trading Framework Backtest")

    # Strategie selectie
    parser.add_argument("--strategy", type=str, default="turtle",
                        choices=["turtle", "ema"],
                        help="Strategy to backtest (default: turtle)", )

    # Periode selectie
    parser.add_argument("--start-date", type=str,
                        help="Start date for backtest (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str,
                        help="End date for backtest (YYYY-MM-DD)")
    parser.add_argument("--period", type=str,
                        help="Predefined period (1m, 3m, 6m, 1y, 2y, 5y)")

    # Symbols en timeframe
    parser.add_argument("--symbols", type=str, nargs="+",
                        help="Symbols to backtest (space separated)")
    parser.add_argument("--timeframe", type=str, default="H4",
                        choices=["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
                        help="Timeframe to use (default: H4)", )

    # Kapitaal en commissie
    parser.add_argument("--initial-cash", type=float, default=10000.0,
                        help="Initial cash for backtest (default: 10000.0)", )
    parser.add_argument("--commission", type=float, default=0.0001,
                        help="Commission rate (default: 0.0001)", )

    # Strategie parameters - Turtle
    parser.add_argument("--entry-period", type=int, default=20,
                        help="Entry period for Turtle strategy (default: 20)", )
    parser.add_argument("--exit-period", type=int, default=10,
                        help="Exit period for Turtle strategy (default: 10)", )
    parser.add_argument("--atr-period", type=int, default=14,
                        help="ATR period for Turtle strategy (default: 14)", )
    parser.add_argument("--risk-pct", type=float, default=0.01,
                        help="Risk percentage per trade (default: 0.01)", )

    # Strategie parameters - EMA
    parser.add_argument("--fast-ema", type=int, default=9,
                        help="Fast EMA period (default: 9)")
    parser.add_argument("--slow-ema", type=int, default=21,
                        help="Slow EMA period (default: 21)")
    parser.add_argument("--signal-ema", type=int, default=5,
                        help="Signal EMA period (default: 5)")

    # Output opties
    parser.add_argument("--plot", action="store_true",
                        help="Generate plot of backtest results")
    parser.add_argument("--output-dir", type=str, default="backtest_results",
                        help="Directory for output files", )
    parser.add_argument("--report", action="store_true",
                        help="Generate detailed HTML report")

    # Optimalisatie
    parser.add_argument("--optimize", action="store_true",
                        help="Run parameter optimization")

    # Configuratie bestand
    parser.add_argument("--config", type=str,
                        help="Path to custom configuration file")

    return parser.parse_args()


def calculate_start_date(period: str) -> str:
    """
    Bereken startdatum gebaseerd op periode.

    Args:
        period: Periode string (1m, 3m, 6m, 1y, 2y, 5y)

    Returns:
        Startdatum als string (YYYY-MM-DD)
    """
    today = datetime.now()

    if period == "1m":
        start = today - timedelta(days=30)
    elif period == "3m":
        start = today - timedelta(days=90)
    elif period == "6m":
        start = today - timedelta(days=180)
    elif period == "1y":
        start = today - timedelta(days=365)
    elif period == "2y":
        start = today - timedelta(days=365 * 2)
    elif period == "5y":
        start = today - timedelta(days=365 * 5)
    else:
        # Default to 1 year
        start = today - timedelta(days=365)

    return start.strftime("%Y-%m-%d")


def run_backtest(args, logger):
    """
    Voer de backtest uit met de gegeven argumenten.

    Args:
        args: Command line argumenten
        logger: Logger instantie
    """
    # Laad configuratie
    config = load_config(args.config)

    # Bepaal startdatum
    if args.start_date:
        start_date = args.start_date
    elif args.period:
        start_date = calculate_start_date(args.period)
    else:
        # Default: 1 jaar terug
        start_date = calculate_start_date("1y")

    # Bepaal einddatum
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")

    # Bepaal symbols
    symbols = args.symbols or config.get("symbols", ["EURUSD"])

    # Backtrader adapter instantiëren
    adapter = BacktraderAdapter(config)

    # Cerebro voorbereiden
    cerebro = adapter.prepare_cerebro(initial_cash=args.initial_cash)

    # Data toevoegen
    for symbol in symbols:
        df = adapter.get_historical_data(symbol, args.timeframe,
                                         from_date=start_date,
                                         to_date=end_date)

        if len(df) > 0:
            adapter.add_data(df, symbol, args.timeframe)
            logger.info(f"Added {symbol} data with {len(df)} bars")
        else:
            logger.warning(f"No data available for {symbol}")

    # Strategie toevoegen op basis van keuze
    if args.strategy == "turtle":
        strategy_params = {"entry_period": args.entry_period,
                           "exit_period": args.exit_period,
                           "atr_period": args.atr_period,
                           "risk_pct": args.risk_pct, "use_vol_filter": True,
                           "vol_lookback": 100,
                           "vol_threshold": 1.2, }
        logger.info(f"Using Turtle strategy with parameters: {strategy_params}")
        adapter.add_strategy(TurtleStrategy, **strategy_params)

    elif args.strategy == "ema":
        strategy_params = {"fast_ema": args.fast_ema, "slow_ema": args.slow_ema,
                           "signal_ema": args.signal_ema,
                           "risk_pct": args.risk_pct,
                           "atr_period": args.atr_period, "atr_multiplier": 2.0,
                           "trail_stop": True, }
        logger.info(f"Using EMA strategy with parameters: {strategy_params}")
        adapter.add_strategy(EMAStrategy, **strategy_params)

    # Maak output directory indien nodig
    output_dir = os.path.join(project_root, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Voer backtest uit
    logger.info(f"Starting backtest from {start_date} to {end_date}")
    results, metrics = adapter.run_backtest()

    # Toon resultaten
    print("\n" + "=" * 80)
    print(f"BACKTEST RESULTS: {args.strategy.upper()} STRATEGY")
    print("=" * 80)

    print(f"\nSymbols: {', '.join(symbols)}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Period: {start_date} to {end_date}")
    print(f"\nInitial capital: ${args.initial_cash:.2f}")
    print(f"Final capital: ${metrics['final_value']:.2f}")
    print(
        f"Net profit/loss: ${metrics['final_value'] - args.initial_cash:.2f} ({metrics['total_return_pct']:.2f}%)")

    # Uitgebreide metrics in tabel vorm
    metrics_table = [["Total Return", f"{metrics['total_return_pct']:.2f}%"],
                     ["Annual Return", f"{metrics['annual_return']:.2f}%"],
                     ["Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}"],
                     ["Max Drawdown", f"{metrics['max_drawdown_pct']:.2f}%"],
                     ["Max Drawdown Length",
                      f"{metrics['max_drawdown_len']} bars"],
                     ["Total Trades", metrics["total_trades"]],
                     ["Win Rate", f"{metrics['win_rate']:.2f}%"],
                     ["Profit Factor", f"{metrics['profit_factor']:.2f}"], ]

    print("\n" + tabulate(metrics_table, headers=["Metric", "Value"],
                          tablefmt="grid"))

    # Plot resultaten indien gevraagd
    if args.plot:
        plot_filename = os.path.join(output_dir,
                                     f"backtest_{args.strategy}_{args.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png", )
        adapter.plot_results(filename=plot_filename)
        print(f"\nPlot saved to: {plot_filename}")

    # Sla resultaten op als json
    results_filename = os.path.join(output_dir,
                                    f"backtest_{args.strategy}_{args.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", )

    with open(results_filename, "w") as f:
        # Metrics en parameters samen opslaan
        results_dict = {"metrics": metrics,
                        "parameters": {"strategy": args.strategy,
                                       "timeframe": args.timeframe,
                                       "start_date": start_date,
                                       "end_date": end_date, "symbols": symbols,
                                       "initial_cash": args.initial_cash,
                                       "strategy_params": strategy_params, }, }
        json.dump(results_dict, f, indent=4)

    print(f"Results saved to: {results_filename}")
    return results, metrics


def main():
    """Hoofdfunctie voor het backtest script."""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Sophia Trading Framework Backtest")

    # Parse argumenten
    args = parse_arguments()

    # Voer backtest uit
    try:
        results, metrics = run_backtest(args, logger)
        return 0
    except Exception as e:
        logger.error(f"Error during backtest: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
