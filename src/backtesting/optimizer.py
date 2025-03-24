#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parameter optimalisatie voor Sophia Trading Framework strategieën.
Zoekt naar optimale parameters voor een strategie via grid search of genetisch algoritme.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate

# Zorg dat het project root path in sys.path zit voor imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.backtesting.backtrader_adapter import BacktraderAdapter
from src.backtesting.strategies.turtle_bt import TurtleStrategy
from src.backtesting.strategies.ema_bt import EMAStrategy


def setup_logging() -> None:
    """Setup logging voor het optimalisatie script."""
    log_dir = os.path.join(project_root, "src", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(
        log_dir, f"optimize_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    # Configureer de logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    return logging.getLogger("sophia.optimize")


def load_config(config_path: Optional[Optional[Optional[str]]] = None) -> Dict[str, Any]:
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


def parse_arguments() -> None:
    """Parse commandline argumenten."""
    parser = argparse.ArgumentParser(
        description="Sophia Trading Framework Strategy Optimizer"
    )

    # Strategie selectie
    parser.add_argument(
        "--strategy",
        type=str,
        default="turtle",
        choices=["turtle", "ema"],
        help="Strategy to optimize (default: turtle)",
    )

    # Periode selectie
    parser.add_argument(
        "--start-date", type=str,
        help="Start date for optimization (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, help="End date for optimization (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--period",
        type=str,
        default="1y",
        help="Predefined period (1m, 3m, 6m, 1y, 2y, 5y)",
    )

    # Symbols en timeframe
    parser.add_argument(
        "--symbols", type=str, nargs="+",
        help="Symbols to optimize (space separated)"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="H4",
        choices=["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
        help="Timeframe to use (default: H4)",
    )

    # Optimalisatie methode
    parser.add_argument(
        "--method",
        type=str,
        default="grid",
        choices=["grid", "genetic"],
        help="Optimization method (default: grid)",
    )

    # Kapitaal
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=10000.0,
        help="Initial cash for backtest (default: 10000.0)",
    )

    # Metric om te optimaliseren
    parser.add_argument(
        "--metric",
        type=str,
        default="sharpe",
        choices=["sharpe", "return", "drawdown", "profit_factor"],
        help="Metric to optimize for (default: sharpe)",
    )

    # Parameter ranges - Turtle
    parser.add_argument(
        "--entry-period-range",
        type=str,
        default="10,20,30,40",
        help="Range for entry_period (default: 10,20,30,40)",
    )
    parser.add_argument(
        "--exit-period-range",
        type=str,
        default="5,10,15,20",
        help="Range for exit_period (default: 5,10,15,20)",
    )
    parser.add_argument(
        "--atr-period-range",
        type=str,
        default="10,14,20",
        help="Range for atr_period (default: 10,14,20)",
    )

    # Parameter ranges - EMA
    parser.add_argument(
        "--fast-ema-range",
        type=str,
        default="5,9,12,15",
        help="Range for fast_ema (default: 5,9,12,15)",
    )
    parser.add_argument(
        "--slow-ema-range",
        type=str,
        default="20,25,30",
        help="Range for slow_ema (default: 20,25,30)",
    )
    parser.add_argument(
        "--signal-ema-range",
        type=str,
        default="5,7,9",
        help="Range for signal_ema (default: 5,7,9)",
    )

    # Output opties
    parser.add_argument(
        "--output-dir",
        type=str,
        default="optimization_results",
        help="Directory for output files",
    )
    parser.add_argument(
        "--max-combinations",
        type=int,
        default=100,
        help="Maximum number of parameter combinations to test",
    )
    parser.add_argument(
        "--plot-top", type=int, default=5, help="Number of top results to plot"
    )

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


def parse_range(range_str: str) -> List[int]:
    """
    Parse een bereik string naar een lijst van integers.

    Args:
        range_str: Bereik als string (bijv. "10,20,30,40")

    Returns:
        Lijst van integers
    """
    try:
        return [int(x.strip()) for x in range_str.split(",")]
    except ValueError:
        print(f"Error parsing range: {range_str}")
        return []


def generate_parameter_combinations(
    args, strategy: str, limit: int
) -> List[Dict[str, Any]]:
    """
    Genereer alle parameter combinaties voor de gegeven strategie.

    Args:
        args: Command line argumenten
        strategy: Naam van de strategie ('turtle' of 'ema')
        limit: Maximum aantal combinaties

    Returns:
        Lijst van parameter dictionaries
    """
    if strategy == "turtle":
        # Parse parameter ranges
        entry_periods = parse_range(args.entry_period_range)
        exit_periods = parse_range(args.exit_period_range)
        atr_periods = parse_range(args.atr_period_range)

        # Alle mogelijke combinaties
        param_combinations = []
        for entry in entry_periods:
            for exit in exit_periods:
                for atr in atr_periods:
                    param_combinations.append(
                        {
                            "entry_period": entry,
                            "exit_period": exit,
                            "atr_period": atr,
                            "risk_pct": 0.01,  # Fixed
                            "use_vol_filter": True,  # Fixed
                            "vol_lookback": 100,  # Fixed
                            "vol_threshold": 1.2,  # Fixed
                        }
                    )

    elif strategy == "ema":
        # Parse parameter ranges
        fast_emas = parse_range(args.fast_ema_range)
        slow_emas = parse_range(args.slow_ema_range)
        signal_emas = parse_range(args.signal_ema_range)

        # Alle mogelijke combinaties
        param_combinations = []
        for fast in fast_emas:
            for slow in slow_emas:
                # Skip ongeldige combinaties (fast moet kleiner zijn dan slow)
                if fast >= slow:
                    continue

                for signal in signal_emas:
                    param_combinations.append(
                        {
                            "fast_ema": fast,
                            "slow_ema": slow,
                            "signal_ema": signal,
                            "risk_pct": 0.01,  # Fixed
                            "atr_period": 14,  # Fixed
                            "atr_multiplier": 2.0,  # Fixed
                            "trail_stop": True,  # Fixed
                        }
                    )

    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    # Beperk aantal combinaties indien nodig
    if len(param_combinations) > limit:
        print(
            f"Limiting parameter combinations from {len(param_combinations)} to {limit}"
        )
        return param_combinations[:limit]

    return param_combinations


def run_optimization(args, logger) -> None:
    """
    Voer de optimalisatie uit met de gegeven argumenten.

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

    # Maak output directory indien nodig
    output_dir = os.path.join(project_root, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Backtrader adapter instantiëren
    adapter = BacktraderAdapter(config)

    # Data voorbereiden
    logger.info("Preparing data for optimization...")
    data_loaded = False

    try:
        # Loop over symbols en haal data op
        for symbol in symbols:
            df = adapter.get_historical_data(
                symbol, args.timeframe, from_date=start_date, to_date=end_date
            )

            if len(df) > 0:
                logger.info(f"Loaded {len(df)} bars for {symbol}")
                data_loaded = True
                adapter.data_cache[f"{symbol}_{args.timeframe}"] = df
            else:
                logger.warning(f"No data available for {symbol}")
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None

    if not data_loaded:
        logger.error("No data could be loaded for optimization")
        return None

    # Genereer parameter combinaties
    logger.info(
        f"Generating parameter combinations for {args.strategy} strategy...")
    param_combinations = generate_parameter_combinations(
        args, args.strategy, args.max_combinations
    )

    logger.info(
        f"Running optimization with {len(param_combinations)} parameter combinations"
    )

    # Optimalisatie resultaten
    results = []

    # Start timer
    start_time = time.time()

    # Loop over alle parameter combinaties
    for i, params in enumerate(param_combinations):
        # Update progress
        if i % 5 == 0 or i == len(param_combinations) - 1:
            elapsed = time.time() - start_time
            remaining = elapsed / (i + 1) * (len(param_combinations) - i - 1)
            print(
                f"Progress: {i + 1}/{len(param_combinations)} combinations - "
                f"Elapsed: {elapsed:.1f}s - Estimated remaining: {remaining:.1f}s",
                end="\r",
            )

        # Backtrader cerebro voorbereiden
        cerebro = adapter.prepare_cerebro(initial_cash=args.initial_cash)

        # Data toevoegen
        for symbol in symbols:
            df = adapter.data_cache.get(f"{symbol}_{args.timeframe}")
            if df is not None and len(df) > 0:
                adapter.add_data(df, symbol, args.timeframe)

        # Strategie toevoegen met de huidige parameters
        if args.strategy == "turtle":
            adapter.add_strategy(TurtleStrategy, **params)
        elif args.strategy == "ema":
            adapter.add_strategy(EMAStrategy, **params)

        # Backtest uitvoeren
        _, metrics = adapter.run_backtest()

        # Metrics opslaan met parameters
        result = {"params": params, "metrics": metrics}

        results.append(result)

    print()  # Nieuwe regel na progress update

    # Sorteer resultaten op basis van gekozen metric
    if args.metric == "sharpe":
        # Hoger is beter
        results.sort(key=lambda x: x["metrics"]["sharpe_ratio"], reverse=True)
        metric_name = "Sharpe Ratio"
    elif args.metric == "return":
        # Hoger is beter
        results.sort(key=lambda x: x["metrics"]["total_return_pct"],
                     reverse=True)
        metric_name = "Total Return %"
    elif args.metric == "drawdown":
        # Lager is beter
        results.sort(key=lambda x: x["metrics"]["max_drawdown_pct"])
        metric_name = "Max Drawdown %"
    elif args.metric == "profit_factor":
        # Hoger is beter
        results.sort(key=lambda x: x["metrics"]["profit_factor"], reverse=True)
        metric_name = "Profit Factor"

    # Toon top resultaten
    top_n = min(10, len(results))

    print("\n" + "=" * 80)
    print(
        f"TOP {top_n} PARAMETER COMBINATIONS FOR {args.strategy.upper()} STRATEGY")
    print("=" * 80)
    print(f"\nOptimized for: {metric_name}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Period: {start_date} to {end_date}")

    # Maak tabel met resultaten
    table_data = []

    for i, result in enumerate(results[:top_n]):
        params = result["params"]
        metrics = result["metrics"]

        # Maak rij specifiek voor elke strategie
        if args.strategy == "turtle":
            row = [
                i + 1,
                params["entry_period"],
                params["exit_period"],
                params["atr_period"],
                f"{metrics['total_return_pct']:.2f}%",
                f"{metrics['sharpe_ratio']:.2f}",
                f"{metrics['max_drawdown_pct']:.2f}%",
                f"{metrics['win_rate']:.2f}%",
                f"{metrics['profit_factor']:.2f}",
                metrics["total_trades"],
            ]
            headers = [
                "Rank",
                "Entry",
                "Exit",
                "ATR",
                "Return %",
                "Sharpe",
                "Drawdown",
                "Win Rate",
                "Profit Factor",
                "Trades",
            ]

        elif args.strategy == "ema":
            row = [
                i + 1,
                params["fast_ema"],
                params["slow_ema"],
                params["signal_ema"],
                f"{metrics['total_return_pct']:.2f}%",
                f"{metrics['sharpe_ratio']:.2f}",
                f"{metrics['max_drawdown_pct']:.2f}%",
                f"{metrics['win_rate']:.2f}%",
                f"{metrics['profit_factor']:.2f}",
                metrics["total_trades"],
            ]
            headers = [
                "Rank",
                "Fast EMA",
                "Slow EMA",
                "Signal EMA",
                "Return %",
                "Sharpe",
                "Drawdown",
                "Win Rate",
                "Profit Factor",
                "Trades",
            ]

        table_data.append(row)

    # Toon tabel
    print("\n" + tabulate(table_data, headers=headers, tablefmt="grid") + "\n")

    # Plot key metrics voor top resultaten
    if args.plot_top > 0:
        num_to_plot = min(args.plot_top, len(results))

        # Selecteer metrics om te plotten
        metrics_to_plot = [
            ("total_return_pct", "Total Return %"),
            ("sharpe_ratio", "Sharpe Ratio"),
            ("max_drawdown_pct", "Max Drawdown %"),
            ("win_rate", "Win Rate %"),
        ]

        # Maak de plot
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()

        # Plot elke metric
        for i, (metric_key, metric_label) in enumerate(metrics_to_plot):
            values = [r["metrics"][metric_key] for r in results[:num_to_plot]]
            ranks = list(range(1, num_to_plot + 1))

            axes[i].bar(ranks, values)
            axes[i].set_title(metric_label)
            axes[i].set_xlabel("Rank")
            axes[i].set_ylabel(metric_label)
            axes[i].grid(True, alpha=0.3)

            # Voeg waarden toe aan de bars
            for j, v in enumerate(values):
                axes[i].text(j + 1, v, f"{v:.2f}", ha="center", va="bottom")

        plt.tight_layout()
        plt.suptitle(
            f"Top {num_to_plot} Parameter Sets for {args.strategy.upper()} Strategy",
            fontsize=16,
            y=1.02,
        )

        # Sla plot op
        plot_filename = os.path.join(
            output_dir,
            f"optimize_{args.strategy}_{args.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )
        plt.savefig(plot_filename, dpi=300, bbox_inches="tight")
        print(f"Plot saved to: {plot_filename}")
        plt.close()

    # Sla resultaten op als json
    results_filename = os.path.join(
        output_dir,
        f"optimize_{args.strategy}_{args.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    with open(results_filename, "w") as f:
        # Als metrics een numpy array bevat, deze converteren naar list
        results_dict = {
            "strategy": args.strategy,
            "timeframe": args.timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "symbols": symbols,
            "metric": args.metric,
            "results": [
                {
                    "params": r["params"],
                    "metrics": {
                        k: float(v) if isinstance(v, (
                        np.float32, np.float64)) else v
                        for k, v in r["metrics"].items()
                    },
                }
                for r in results
            ],
        }
        json.dump(results_dict, f, indent=4)

    print(f"Optimization results saved to: {results_filename}")

    # Vraag de gebruiker of ze het beste resultaat willen opslaan in de configuratie
    best_params = results[0]["params"] if results else None

    if best_params:
        print("\n" + "=" * 80)
        print("BEST PARAMETERS FOUND:")
        for k, v in best_params.items():
            print(f"  {k}: {v}")

        if args.strategy == "turtle":
            print("\nCommands to run backtest with these parameters:")
            print(
                f"python -m src.analysis.backtest --strategy turtle --entry-period {best_params['entry_period']} "
                f"--exit-period {best_params['exit_period']} --atr-period {best_params['atr_period']} "
                f"--timeframe {args.timeframe} --plot"
            )
        elif args.strategy == "ema":
            print("\nCommands to run backtest with these parameters:")
            print(
                f"python -m src.analysis.backtest --strategy ema --fast-ema {best_params['fast_ema']} "
                f"--slow-ema {best_params['slow_ema']} --signal-ema {best_params['signal_ema']} "
                f"--timeframe {args.timeframe} --plot"
            )

    return results


def main() -> None:
    """Hoofdfunctie voor het optimalisatie script."""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Sophia Trading Framework Strategy Optimizer")

    # Parse argumenten
    args = parse_arguments()

    # Voer optimalisatie uit
    try:
        results = run_optimization(args, logger)
        if results:
            return 0
        else:
            return 1
    except Exception as e:
        logger.error(f"Error during optimization: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

