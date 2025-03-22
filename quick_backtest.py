# Bestandsnaam: quick_backtest.py
# Locatie: Project root (hoofdmap van je project)

# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Snel backtest script voor Sophia Trading Framework.
"""
import argparse
import os
import subprocess
import sys


def main():
    """
    Snel backtest script met profielselectie.
    """
    parser = argparse.ArgumentParser(description="Quick Backtest Runner")

    # Profiel selectie
    parser.add_argument("--profile", type=str,
                        help="Naam van een opgeslagen profiel")

    # Of directe parameter overrides
    parser.add_argument("--strategy", type=str, choices=["turtle", "ema"],
                        help="Strategie om te backtesten")
    parser.add_argument("--symbols", type=str,
                        help="Komma-gescheiden lijst van symbolen")
    parser.add_argument("--timeframe", type=str,
                        help="Timeframe (M1, M5, H1, H4, D1)")
    parser.add_argument("--period", type=str, help="Periode (1m, 3m, 6m, 1y)")

    args = parser.parse_args()

    # Script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = script_dir  # Aangezien dit script in de project root staat

    # Laad profiel indien opgegeven
    if args.profile:
        profile_file = os.path.join(project_root, "backtest_profiles",
                                    f"{args.profile}.json")
        if not os.path.exists(profile_file):
            print(f"ERROR: Profiel {args.profile} niet gevonden")
            return 1

        try:
            import json
            with open(profile_file, "r") as f:
                profile = json.load(f)

            # Command opbouwen
            cmd = [
                sys.executable,
                "-m",
                "src.analysis.backtest",
                "--strategy", profile["strategy"],
                "--timeframe", profile["timeframe"],
                "--period", profile["period"],
                "--initial-cash", profile["initial_cash"],
                "--symbols"
            ]

            # Symbolen toevoegen
            symbols = [s.strip() for s in profile["symbols"].split(",") if
                       s.strip()]
            cmd.extend(symbols)

            # Strategie parameters toevoegen
            if profile["strategy"] == "turtle":
                cmd.extend([
                    "--entry-period",
                    profile["strategy_params"]["entry_period"],
                    "--exit-period", profile["strategy_params"]["exit_period"],
                    "--atr-period", profile["strategy_params"]["atr_period"],
                ])
            else:  # EMA
                cmd.extend([
                    "--fast-ema", profile["strategy_params"]["fast_ema"],
                    "--slow-ema", profile["strategy_params"]["slow_ema"],
                    "--signal-ema", profile["strategy_params"]["signal_ema"],
                ])

            # Plot toevoegen indien ingeschakeld
            if profile.get("plot", True):
                cmd.append("--plot")

        except Exception as e:
            print(f"ERROR: Kon profiel niet laden: {e}")
            return 1
    else:
        # Directe commando opbouwen
        if not args.strategy or not args.symbols or not args.timeframe:
            print(
                "ERROR: Geef of een --profile op of --strategy, --symbols en --timeframe")
            return 1

        cmd = [
            sys.executable,
            "-m",
            "src.analysis.backtest",
            "--strategy", args.strategy,
            "--timeframe", args.timeframe,
            "--symbols"
        ]

        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        cmd.extend(symbols)

        if args.period:
            cmd.extend(["--period", args.period])

        # Standaard plot toevoegen
        cmd.append("--plot")

    # Uitvoeren
    print(f"Uitvoeren: {' '.join(cmd)}")
    subprocess.run(cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
