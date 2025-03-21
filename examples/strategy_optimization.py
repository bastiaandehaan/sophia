#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Voorbeeldscript voor het optimaliseren van een strategie en vervolgens backtesten
van de beste parameters. Dit script laat zien hoe je de Sophia Trading Framework
kunt gebruiken voor het vinden van optimale parameters en het evalueren van de strategie.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

# Zorg dat project root in sys.path zit
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.analysis.backtrader_adapter import BacktraderAdapter
from src.analysis.strategies.turtle_bt import TurtleStrategy
from src.analysis.strategies.ema_bt import EMAStrategy


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Strategie optimalisatie en backtest voorbeeld"
    )

    parser.add_argument(
        "--strategy",
        type=str,
        default="turtle",
        choices=["turtle", "ema"],
        help="Strategie om te optimaliseren (default: turtle)",
    )

    parser.add_argument(
        "--symbol",
        type=str,
        default="EURUSD",
        help="Symbool om te testen (default: EURUSD)",
    )

    parser.add_argument(
        "--timeframe",
        type=str,
        default="H4",
        choices=["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
        help="Timeframe voor data (default: H4)",
    )

    parser.add_argument(
        "--period",
        type=str,
        default="1y",
        choices=["1m", "3m", "6m", "1y", "2y", "5y"],
        help="Periode voor backtest (default: 1y)",
    )

    parser.add_argument(
        "--metric",
        type=str,
        default="sharpe",
        choices=["sharpe", "return", "drawdown", "profit_factor"],
        help="Metric om te optimaliseren (default: sharpe)",
    )

    parser.add_argument(
        "--combinations",
        type=int,
        default=25,
        help="Aantal parametercombinaties om te testen (default: 25)",
    )

    return parser.parse_args()


def calculate_period_dates(period):
    """
    Bereken start- en einddatum op basis van periode.

    Args:
        period: Periode string (1m, 3m, 6m, 1y, 2y, 5y)

    Returns:
        Tuple met (startdatum, einddatum) als strings (YYYY-MM-DD)
    """
    end_date = datetime.now()

    if period == "1m":
        start_date = end_date - timedelta(days=30)
    elif period == "3m":
        start_date = end_date - timedelta(days=90)
    elif period == "6m":
        start_date = end_date - timedelta(days=180)
    elif period == "1y":
        start_date = end_date - timedelta(days=365)
    elif period == "2y":
        start_date = end_date - timedelta(days=365 * 2)
    elif period == "5y":
        start_date = end_date - timedelta(days=365 * 5)
    else:
        # Default to 1 year
        start_date = end_date - timedelta(days=365)

    return (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))


def generate_parameter_combinations(strategy, num_combinations):
    """
    Genereer parameter combinaties voor de gegeven strategie.

    Args:
        strategy: Naam van de strategie ('turtle' of 'ema')
        num_combinations: Maximum aantal combinaties

    Returns:
        Lijst van parameter dictionaries
    """
    if strategy == "turtle":
        # Parameter bereiken voor Turtle strategy
        entry_periods = [10, 15, 20, 25, 30, 40]
        exit_periods = [5, 8, 10, 12, 15, 20]
        atr_periods = [10, 14, 20]
        use_vol_filters = [True, False]

        # Genereer combinaties
        combinations = []
        for entry in entry_periods:
            for exit in exit_periods:
                if exit >= entry:  # Skip ongeldige combinaties
                    continue
                for atr in atr_periods:
                    for vol_filter in use_vol_filters:
                        combinations.append(
                            {
                                "entry_period": entry,
                                "exit_period": exit,
                                "atr_period": atr,
                                "use_vol_filter": vol_filter,
                                "risk_pct": 0.01,  # Vast
                            }
                        )

                        # Stop als we maximum bereiken
                        if len(combinations) >= num_combinations:
                            return combinations[:num_combinations]

    elif strategy == "ema":
        # Parameter bereiken voor EMA strategy
        fast_emas = [5, 8, 9, 10, 12, 15]
        slow_emas = [18, 20, 21, 25, 30]
        signal_emas = [3, 5, 7, 9]

        # Genereer combinaties
        combinations = []
        for fast in fast_emas:
            for slow in slow_emas:
                if fast >= slow:  # Skip ongeldige combinaties
                    continue
                for signal in signal_emas:
                    combinations.append(
                        {
                            "fast_ema": fast,
                            "slow_ema": slow,
                            "signal_ema": signal,
                            "risk_pct": 0.01,  # Vast
                            "trail_stop": True,  # Vast
                        }
                    )

                    # Stop als we maximum bereiken
                    if len(combinations) >= num_combinations:
                        return combinations[:num_combinations]

    return combinations


def run_parameter_optimization(args):
    """
    Voer parameter optimalisatie uit voor de gegeven strategie.

    Args:
        args: Command line argumenten

    Returns:
        Dict met beste parameters
    """
    print(f"\n{'=' * 80}")
    print(f"PARAMETER OPTIMALISATIE: {args.strategy.upper()} STRATEGIE")
    print(f"{'=' * 80}")

    # Bereken periode datums
    start_date, end_date = calculate_period_dates(args.period)
    print(f"Periode: {start_date} tot {end_date}")
    print(f"Symbool: {args.symbol}, Timeframe: {args.timeframe}")
    print(f"Optimalisatie metric: {args.metric}")
    print(f"Maximum combinaties: {args.combinations}")

    # Initialiseer adapter
    adapter = BacktraderAdapter()

    # Haal historische data op
    print(f"\nHistorische data ophalen voor {args.symbol}...")
    data = adapter.get_historical_data(
        args.symbol, args.timeframe, from_date=start_date, to_date=end_date
    )

    if data is None or len(data) == 0:
        print(
            "Kon geen historische data ophalen. Controleer symbool en datums.")
        return None

    print(
        f"Opgehaald: {len(data)} bars van {data['time'].min()} tot {data['time'].max()}"
    )

    # Genereer parameter combinaties
    parameter_combinations = generate_parameter_combinations(
        args.strategy, args.combinations
    )

    print(
        f"\nTesten van {len(parameter_combinations)} parameter combinaties...")

    # Resultaten opslaan
    results = []

    # Loop door alle parameter combinaties
    for i, params in enumerate(parameter_combinations):
        print(f"Test {i + 1}/{len(parameter_combinations)}: {params}", end="\r")

        # Reset Cerebro
        cerebro = adapter.prepare_cerebro(initial_cash=10000.0)

        # Voeg data toe
        adapter.add_data(data.copy(), args.symbol, args.timeframe)

        # Voeg strategie toe met deze parameters
        if args.strategy == "turtle":
            adapter.add_strategy(TurtleStrategy, **params)
        else:  # ema
            adapter.add_strategy(EMAStrategy, **params)

        # Run backtest
        _, metrics = adapter.run_backtest()

        # Sla resultaten op
        results.append({"params": params, "metrics": metrics})

    print("\n\nOptimalisatie voltooid!")

    # Sorteer resultaten op basis van gekozen metric
    if args.metric == "sharpe":
        # Hoger is beter
        results.sort(key=lambda x: x["metrics"]["sharpe_ratio"], reverse=True)
        metric_name = "Sharpe Ratio"
        metric_key = "sharpe_ratio"
    elif args.metric == "return":
        # Hoger is beter
        results.sort(key=lambda x: x["metrics"]["total_return_pct"],
                     reverse=True)
        metric_name = "Total Return %"
        metric_key = "total_return_pct"
    elif args.metric == "drawdown":
        # Lager is beter
        results.sort(key=lambda x: x["metrics"]["max_drawdown_pct"])
        metric_name = "Max Drawdown %"
        metric_key = "max_drawdown_pct"
    elif args.metric == "profit_factor":
        # Hoger is beter
        results.sort(key=lambda x: x["metrics"]["profit_factor"], reverse=True)
        metric_name = "Profit Factor"
        metric_key = "profit_factor"

    # Toon top 5 resultaten
    print(
        f"\nTop 5 {args.strategy.upper()} parameters (gesorteerd op {metric_name}):")
    print(f"{'=' * 80}")
    for i, result in enumerate(results[:5]):
        params_str = ", ".join(
            [f"{k}={v}" for k, v in result["params"].items()])
        metrics_str = (
            f"{metric_name}: {result['metrics'][metric_key]:.2f}, "
            f"Return: {result['metrics']['total_return_pct']:.2f}%, "
            f"Drawdown: {result['metrics']['max_drawdown_pct']:.2f}%, "
            f"Trades: {result['metrics']['total_trades']}"
        )
        print(f"{i + 1}. {params_str}")
        print(f"   {metrics_str}")

    # Bewaar beste parameters
    best_params = results[0]["params"]

    # Sla resultaten op in JSON bestand
    output_dir = "optimization_results"
    os.makedirs(output_dir, exist_ok=True)

    results_file = os.path.join(
        output_dir,
        f"optimize_{args.strategy}_{args.symbol}_{args.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    with open(results_file, "w") as f:
        json.dump(
            {
                "strategy": args.strategy,
                "symbol": args.symbol,
                "timeframe": args.timeframe,
                "period": args.period,
                "start_date": start_date,
                "end_date": end_date,
                "metric": args.metric,
                "results": results[:10],  # Bewaar top 10
            },
            f,
            indent=2,
        )

    print(f"\nResultaten opgeslagen in: {results_file}")

    return best_params


def run_backtest_with_parameters(args, params):
    """
    Voer een backtest uit met de gegeven parameters.

    Args:
        args: Command line argumenten
        params: Parameters dictionary
    """
    print(f"\n{'=' * 80}")
    print(
        f"BACKTEST MET OPTIMALE PARAMETERS: {args.strategy.upper()} STRATEGIE")
    print(f"{'=' * 80}")

    # Bereken periode datums
    start_date, end_date = calculate_period_dates(args.period)
    print(f"Periode: {start_date} tot {end_date}")
    print(f"Symbool: {args.symbol}, Timeframe: {args.timeframe}")

    # Toon parameters
    print("\nParameters:")
    for k, v in params.items():
        print(f"  {k}: {v}")

    # Initialiseer adapter
    adapter = BacktraderAdapter()

    # Haal historische data op
    print(f"\nHistorische data ophalen voor {args.symbol}...")
    data = adapter.get_historical_data(
        args.symbol, args.timeframe, from_date=start_date, to_date=end_date
    )

    # Initialiseer Cerebro
    cerebro = adapter.prepare_cerebro(initial_cash=10000.0)

    # Voeg data toe
    adapter.add_data(data, args.symbol, args.timeframe)

    # Voeg strategie toe met optimale parameters
    if args.strategy == "turtle":
        adapter.add_strategy(TurtleStrategy, **params)
    else:  # ema
        adapter.add_strategy(EMAStrategy, **params)

    # Run backtest
    print("\nBacktest uitvoeren...")
    results, metrics = adapter.run_backtest()

    # Toon metrics
    print("\nBacktest resultaten:")
    print(f"{'=' * 80}")
    print(f"Initial balance: ${cerebro.broker.startingcash:.2f}")
    print(f"Final balance:   ${metrics['final_value']:.2f}")
    print(
        f"Net profit/loss: ${metrics['final_value'] - cerebro.broker.startingcash:.2f} ({metrics['total_return_pct']:.2f}%)"
    )
    print(f"Sharpe ratio:    {metrics['sharpe_ratio']:.2f}")
    print(f"Max drawdown:    {metrics['max_drawdown_pct']:.2f}%")
    print(f"Win rate:        {metrics['win_rate']:.2f}%")
    print(f"Profit factor:   {metrics['profit_factor']:.2f}")
    print(f"Total trades:    {metrics['total_trades']}")

    # Maak plot
    output_dir = "backtest_results"
    os.makedirs(output_dir, exist_ok=True)

    plot_file = os.path.join(
        output_dir,
        f"backtest_{args.strategy}_{args.symbol}_{args.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
    )

    # Plot resultaten
    adapter.plot_results(filename=plot_file)
    print(f"\nPlot opgeslagen in: {plot_file}")

    # Sla configuratie op voor live trading
    config_file = os.path.join(
        output_dir,
        f"config_{args.strategy}_{args.symbol}_{args.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    # Maak config voor live trading
    live_config = {
        "mt5": {
            "server": "FTMO-Demo2",
            "login": 0,  # Vul in voor live trading
            "password": "",  # Vul in voor live trading
            "mt5_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
        },
        "symbols": [args.symbol],
        "timeframe": args.timeframe,
        "interval": 300,
        "risk": {"risk_per_trade": 0.01, "max_daily_loss": 0.05},
        "strategy": {"type": args.strategy, **params},
        # Voeg optimale parameters toe
    }

    with open(config_file, "w") as f:
        json.dump(live_config, f, indent=2)

    print(f"Live trading configuratie opgeslagen in: {config_file}")
    print("\nOm te starten met live trading, gebruik:")
    print(f"python -m src.main --config {config_file}")


def main():
    """Hoofdfunctie voor het voorbeeldscript."""
    # Parse arguments
    args = parse_arguments()

    # Voer parameter optimalisatie uit
    best_params = run_parameter_optimization(args)

    if best_params:
        # Voer backtest uit met beste parameters
        run_backtest_with_parameters(args, best_params)
    else:
        print(
            "Kon geen optimale parameters vinden. Controleer mogelijke fouten.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
