#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sophia Trading Framework Dashboard
Een moderne interface voor backtesting, optimalisatie en analyse van trading strategieën.

Auteur: Sophia Trading Framework Team
Versie: 2.0
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union, Callable

import altair as alt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# Configureer logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sophia.dashboard")

# Configureer pagina-instellingen
st.set_page_config(
    page_title="Sophia Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Zorg dat project root in sys.path staat
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Probeer framework modules te importeren
try:
    from src.core.utils import load_config as core_load_config, \
        save_config as core_save_config
    from src.core.connector import MT5Connector
    from src.backtesting.backtrader_adapter import BacktraderAdapter

    SOPHIA_IMPORTS_SUCCESS = True
except ImportError as e:
    SOPHIA_IMPORTS_SUCCESS = False
    import_error = str(e)
    logger.error(f"Import error: {import_error}")

# Definieer directory paden als Path objecten
CONFIG_DIR = Path(project_root) / "config"
BACKTEST_RESULTS_DIR = Path(project_root) / "backtest_results"
OPTIMIZE_RESULTS_DIR = Path(project_root) / "optimization_results"
PROFILE_DIR = Path(project_root) / "backtest_profiles"
LOG_DIR = Path(project_root) / "src" / "logs"

# Zorg dat alle benodigde directories bestaan
for directory in [CONFIG_DIR, BACKTEST_RESULTS_DIR, OPTIMIZE_RESULTS_DIR,
                  PROFILE_DIR, LOG_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# Definieer constanten
VALID_SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "USDCAD", "AUDUSD", "EURJPY",
                 "EURGBP"]
VALID_TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
PERIODS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "2y": 730, "5y": 1825}

# Initialiseer default session state als die nog niet bestaat
if 'initialized' not in st.session_state:
    # Backtest parameters
    st.session_state.backtest_params = {
        "strategy": "turtle",
        "symbols": "EURUSD",
        "timeframe": "H4",
        "period": "1y",
        "initial_cash": 10000,
        "plot": True,
        "entry_period": 20,
        "exit_period": 10,
        "atr_period": 14,
        "vol_filter": True,
        "fast_ema": 9,
        "slow_ema": 21,
        "signal_ema": 5,
        "rsi_period": 14,
    }

    # Optimalisatie parameters
    st.session_state.optimize_params = {
        "strategy": "turtle",
        "symbols": "EURUSD",
        "timeframe": "H4",
        "period": "1y",
        "metric": "sharpe",
        "max_combinations": 50,
        "entry_range": "10,20,30,40",
        "exit_range": "5,10,15,20",
        "atr_range": "10,14,20",
        "fast_ema_range": "5,9,12,15",
        "slow_ema_range": "20,25,30",
        "signal_ema_range": "5,7,9",
    }

    # Datavisualisatie parameters
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    st.session_state.data_params = {
        "symbol": "EURUSD",
        "timeframe": "H4",
        "from_date": one_year_ago,
        "to_date": today,
        "indicators": {
            "show_ema": True,
            "show_bb": False,
            "show_volume": True,
            "ema1": 9,
            "ema2": 21,
        }
    }

    # Uitvoering en resultaten tracking
    st.session_state.output_lines = []
    st.session_state.running_process = False
    st.session_state.last_run_id = None
    st.session_state.process_progress = 0
    st.session_state.last_backtest_result = None
    st.session_state.last_optimize_result = None
    st.session_state.chart_data = None

    # Opgeslagen profielen
    st.session_state.profiles = []

    # Dashboard status
    st.session_state.active_tab = "Backtesting"
    st.session_state.show_debug = False

    # Markeer als geïnitialiseerd
    st.session_state.initialized = True


# -- Helper Functies --

def load_config(config_path: Optional[Optional[Optional[Union[str, Path]]]] = None) -> Dict[str, Any]:
    """Laad configuratie uit JSON bestand."""
    if config_path is None:
        config_path = CONFIG_DIR / "settings.json"

    try:
        if Path(config_path).exists():
            with open(config_path, "r") as f:
                return json.load(f)
        else:
            logger.warning(f"Configuratiebestand {config_path} niet gevonden")
            return {}
    except Exception as e:
        logger.error(f"Fout bij laden configuratie: {e}")
        return {}


def save_config(config: Dict[str, Any],
                config_path: Optional[Optional[Optional[Union[str, Path]]]] = None) -> bool:
    """Sla configuratie op naar JSON bestand."""
    if config_path is None:
        config_path = CONFIG_DIR / "settings.json"

    try:
        Path(config_path).parent.mkdir(exist_ok=True, parents=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuratie opgeslagen naar {config_path}")
        return True
    except Exception as e:
        logger.error(f"Fout bij opslaan configuratie: {e}")
        return False


def generate_demo_data(symbol: str, from_date: str,
                       to_date: str) -> pd.DataFrame:
    """Genereer demo data voor visualisatie."""
    logger.info(
        f"Genereren van demo data voor {symbol} van {from_date} tot {to_date}")

    # Converteer string datums naar datetime
    start_date = pd.to_datetime(from_date)
    end_date = pd.to_datetime(to_date)

    # Genereer tijdreeks
    date_range = pd.date_range(start=start_date, end=end_date,
                               freq="h")  # Correcte aanroep
    n = len(date_range)

    # Genereer prijzen met realistische bewegingen
    np.random.seed(42)  # Voor consistente resultaten

    # Base price afhankelijk van currency pair
    base = 1.1 if "USD" in symbol else 100.0 if "JPY" in symbol else 1.5

    # Random walk voor prijsbeweging
    changes = np.random.normal(0, 0.0008, n).cumsum()
    close = base + changes

    # Genereer realistische OHLC data
    daily_volatility = 0.008  # ongeveer 0.8% per dag
    high = close + np.abs(np.random.normal(0, daily_volatility / 2, n))
    low = close - np.abs(np.random.normal(0, daily_volatility / 2, n))

    # Zorg dat open binnen high-low range valt
    open_price = low + (high - low) * np.random.random(n)

    # Correcties voor consistentie
    high = np.maximum(high, np.maximum(close, open_price))
    low = np.minimum(low, np.minimum(close, open_price))

    # Volumedata - meer bij grotere prijsveranderingen
    price_changes = np.abs(np.diff(np.append(base, close)))
    volume_base = np.random.randint(100, 1000, n)
    volume = volume_base + (
        price_changes / np.mean(price_changes) * 500).astype(int)

    # Creëer DataFrame
    df = pd.DataFrame({
        "time": date_range,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "tick_volume": volume,
    })

    logger.info(f"Demo data gegenereerd: {len(df)} rijen")
    return df


def fetch_mt5_data(symbol: str, timeframe: str, from_date: str,
                   to_date: str) -> pd.DataFrame:
    """Haal data op van MT5 of genereer demo data als fallback."""

    logger.info(
        f"Data ophalen voor {symbol} {timeframe} van {from_date} tot {to_date}")

    if SOPHIA_IMPORTS_SUCCESS:
        try:
            mt5_config = load_config().get("mt5", {})
            if not mt5_config:
                st.warning(
                    "Geen MT5 configuratie gevonden. Controleer settings.json.")
                return generate_demo_data(symbol, from_date, to_date)

            # Maak verbinding met MT5
            connector = MT5Connector(mt5_config)
            connected = connector.connect()

            if connected:
                logger.info(f"Verbonden met MT5, data ophalen...")
                df = connector.get_historical_data(
                    symbol,
                    timeframe,
                    from_date=from_date,
                    to_date=to_date
                )
                connector.disconnect()

                if df is not None and len(df) > 0:
                    logger.info(f"Data opgehaald: {len(df)} rijen")
                    return df
                else:
                    logger.warning(f"Geen data ontvangen voor {symbol}")
            else:
                logger.error("Kon geen verbinding maken met MT5")
        except Exception as e:
            logger.error(f"Fout bij ophalen MT5 data: {e}")
            st.warning(f"Kon geen data ophalen van MT5: {e}")

    # Fallback naar demo data
    return generate_demo_data(symbol, from_date, to_date)


def save_profile(name: str, parameters: Dict[str, Any]) -> bool:
    """Sla parameters op als profiel."""
    if not name:
        return False

    # Sanitize profile name (remove special characters)
    clean_name = "".join(c for c in name if c.isalnum() or c in "_ -").strip()
    if not clean_name:
        clean_name = "profile"

    filepath = PROFILE_DIR / f"{clean_name}.json"

    try:
        with open(filepath, "w") as f:
            json.dump(parameters, f, indent=2)
        logger.info(f"Profiel opgeslagen: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Fout bij opslaan profiel: {e}")
        return False


def load_profiles() -> List[Dict[str, Any]]:
    """Laad beschikbare profielen."""
    profiles = []

    try:
        profile_files = list(PROFILE_DIR.glob("*.json"))
        for filepath in profile_files:
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                # Converteer symbolen naar string als het een lijst is
                if isinstance(data.get("symbols"), list):
                    data["symbols"] = ",".join(data["symbols"])

                profiles.append({
                    "name": filepath.stem,
                    "filepath": str(filepath),
                    "strategy": data.get("strategy", "unknown"),
                    "symbols": data.get("symbols", "unknown"),
                    "timeframe": data.get("timeframe", "unknown"),
                    "data": data
                })
            except Exception as e:
                logger.error(f"Fout bij laden profiel {filepath.name}: {e}")

    except Exception as e:
        logger.error(f"Fout bij zoeken naar profielen: {e}")

    # Sorteer op naam
    return sorted(profiles, key=lambda x: x["name"])


def load_backtest_results() -> List[Dict[str, Any]]:
    """Laad bestaande backtest resultaten."""
    results = []

    try:
        result_files = list(BACKTEST_RESULTS_DIR.glob("*.json"))
        for filepath in result_files:
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                # Parse datum uit bestandsnaam
                date_str = filepath.stem.split("_")[-1]
                try:
                    date = datetime.strptime(date_str,
                                             "%Y%m%d_%H%M%S").strftime(
                        "%Y-%m-%d %H:%M")
                except ValueError:
                    date = "Onbekend"

                # Extract parameters
                params = data.get("parameters", {})
                metrics = data.get("metrics", {})

                # Check voor potentiële plot
                plot_path = str(filepath).replace(".json", ".png")
                has_plot = os.path.exists(plot_path)

                # Maak entry
                results.append({
                    "date": date,
                    "type": "backtest",
                    "filepath": str(filepath),
                    "strategy": params.get("strategy", "unknown"),
                    "symbol": ", ".join(
                        params.get("symbols", ["unknown"])) if isinstance(
                        params.get("symbols"), list) else "unknown",
                    "timeframe": params.get("timeframe", "unknown"),
                    "period": f"{params.get('start_date', 'x')} tot {params.get('end_date', 'x')}",
                    "return": metrics.get("total_return_pct", 0),
                    "sharpe": metrics.get("sharpe_ratio", 0),
                    "drawdown": metrics.get("max_drawdown_pct", 0),
                    "trades": metrics.get("total_trades", 0),
                    "win_rate": metrics.get("win_rate", 0),
                    "profit_factor": metrics.get("profit_factor", 1),
                    "has_plot": has_plot,
                    "plot_path": plot_path if has_plot else None,
                    "raw_data": data
                })
            except Exception as e:
                logger.error(f"Fout bij laden resultaat {filepath.name}: {e}")

    except Exception as e:
        logger.error(f"Fout bij zoeken naar resultaten: {e}")

    # Sorteer op datum (nieuwste eerst)
    return sorted(results, key=lambda x: x["date"], reverse=True)


def load_optimization_results() -> List[Dict[str, Any]]:
    """Laad bestaande optimalisatie resultaten."""
    results = []

    try:
        result_files = list(OPTIMIZE_RESULTS_DIR.glob("*.json"))
        for filepath in result_files:
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                # Parse datum uit bestandsnaam
                date_str = filepath.stem.split("_")[-1]
                try:
                    date = datetime.strptime(date_str,
                                             "%Y%m%d_%H%M%S").strftime(
                        "%Y-%m-%d %H:%M")
                except ValueError:
                    date = "Onbekend"

                # Get best result if available
                best_result = data.get("results", [{}])[0] if data.get(
                    "results") else {}
                best_params = best_result.get("params", {})
                best_metrics = best_result.get("metrics", {})

                # Check voor potentiële plot
                plot_path = str(filepath).replace(".json", ".png")
                has_plot = os.path.exists(plot_path)

                # Maak entry
                results.append({
                    "date": date,
                    "type": "optimize",
                    "filepath": str(filepath),
                    "strategy": data.get("strategy", "unknown"),
                    "symbol": data.get("symbol", "unknown"),
                    "timeframe": data.get("timeframe", "unknown"),
                    "period": f"{data.get('start_date', 'x')} tot {data.get('end_date', 'x')}",
                    "metric": data.get("metric", "unknown"),
                    "combinations": len(data.get("results", [])),
                    "best_params": best_params,
                    "return": best_metrics.get("total_return_pct", 0),
                    "sharpe": best_metrics.get("sharpe_ratio", 0),
                    "drawdown": best_metrics.get("max_drawdown_pct", 0),
                    "trades": best_metrics.get("total_trades", 0),
                    "has_plot": has_plot,
                    "plot_path": plot_path if has_plot else None,
                    "raw_data": data
                })
            except Exception as e:
                logger.error(
                    f"Fout bij laden optimalisatie {filepath.name}: {e}")

    except Exception as e:
        logger.error(f"Fout bij zoeken naar optimalisaties: {e}")

    # Sorteer op datum (nieuwste eerst)
    return sorted(results, key=lambda x: x["date"], reverse=True)


def run_command(
    command: List[str],
    output_callback: Optional[Optional[Optional[Optional[Callable[[str], None]]]]] = None,
    update_progress: bool = True
) -> Tuple[int, List[str]]:
    """Voer een opdracht uit en verwerk de uitvoer."""

    logger.info(f"Commando uitvoeren: {' '.join(command)}")

    if not update_progress:
        # Eenvoudige uitvoering zonder voortgangsupdates
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        output = []
        for line in process.stdout:
            line = line.strip()
            output.append(line)
            if output_callback:
                output_callback(line)

        process.wait()
        return process.returncode, output

    # Reset progress tracking
    st.session_state.process_progress = 0
    progress_placeholder = st.empty()
    progress_bar = progress_placeholder.progress(0)

    # Start proces
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    # Tracking variabelen
    output = []
    start_time = time.time()
    progress_patterns = {
        "Loading data": 10,
        "Running backtest": 30,
        "Backtest complete": 80,
        "Results saved": 90,
        "Plot saved": 95,
        # Optimization specific
        "Testing parameter combinations": 20,
        "Optimization completed": 80
    }

    # Process uitvoer
    for line in process.stdout:
        line = line.strip()
        current_time = time.time()
        elapsed = current_time - start_time

        # Update voortgangsbalk
        for pattern, value in progress_patterns.items():
            if pattern in line and st.session_state.process_progress < value:
                st.session_state.process_progress = value
                progress_bar.progress(st.session_state.process_progress)
                break

        # ETA schatting toevoegen op basis van voortgang
        if st.session_state.process_progress > 0:
            eta = (elapsed / st.session_state.process_progress) * (
                100 - st.session_state.process_progress)
            line += f" [ETA: {eta:.1f}s]"

        # Bewaar output
        output.append(line)

        # Callback voor UI updates
        if output_callback:
            output_callback(line)

    # Afronding
    process.wait()
    progress_bar.progress(100)

    # Na een korte vertraging, verwijder de voortgangsbalk
    time.sleep(0.5)
    progress_placeholder.empty()

    return process.returncode, output


def run_backtest(params: Dict[str, Any],
                 output_callback: Optional[Optional[Optional[Optional[Callable[[str], None]]]]] = None) -> \
    Tuple[int, List[str]]:
    """Voer een backtest uit met de gegeven parameters."""

    # Bouw commando
    command = ["python", "-m", "src.backtesting.backtest"]

    # Basis parameters
    command.extend(["--strategy", params["strategy"]])

    # Symbolen
    symbols = params.get("symbols", "").strip()
    if symbols:
        command.extend(["--symbols"] + symbols.split(","))
    else:
        command.extend(["--symbols", "EURUSD"])  # Default

    # Timeframe en periode
    command.extend(["--timeframe", params.get("timeframe", "H4")])
    command.extend(["--period", params.get("period", "1y")])

    # Initieel kapitaal
    command.extend(["--initial-cash", str(params.get("initial_cash", 10000))])

    # Strategie-specifieke parameters
    if params.get("strategy") == "turtle":
        command.extend(["--entry-period", str(params.get("entry_period", 20))])
        command.extend(["--exit-period", str(params.get("exit_period", 10))])
        command.extend(["--atr-period", str(params.get("atr_period", 14))])
        if params.get("vol_filter", False):
            command.append("--use-vol-filter")
    else:  # ema
        command.extend(["--fast-ema", str(params.get("fast_ema", 9))])
        command.extend(["--slow-ema", str(params.get("slow_ema", 21))])
        command.extend(["--signal-ema", str(params.get("signal_ema", 5))])
        command.extend(["--rsi-period", str(params.get("rsi_period", 14))])

    # Output opties
    if params.get("plot", True):
        command.append("--plot")

    # Voer commando uit
    return run_command(command, output_callback)


def run_optimization(params: Dict[str, Any],
                     output_callback: Optional[Optional[Optional[Optional[Callable[[str], None]]]]] = None) -> \
    Tuple[int, List[str]]:
    """Voer een optimalisatie uit met de gegeven parameters."""

    # Bouw commando
    command = ["python", "-m", "src.backtesting.optimizer"]

    # Basis parameters
    command.extend(["--strategy", params["strategy"]])

    # Symbolen
    symbols = params.get("symbols", "").strip()
    if symbols:
        command.extend(["--symbols"] + symbols.split(","))
    else:
        command.extend(["--symbols", "EURUSD"])  # Default

    # Timeframe en periode
    command.extend(["--timeframe", params.get("timeframe", "H4")])
    command.extend(["--period", params.get("period", "1y")])

    # Optimalisatie metric en limiet
    command.extend(["--metric", params.get("metric", "sharpe")])
    command.extend(
        ["--max-combinations", str(params.get("max_combinations", 50))])

    # Strategie-specifieke parameter ranges
    if params.get("strategy") == "turtle":
        if "entry_range" in params:
            command.extend(["--entry-period-range", params["entry_range"]])
        if "exit_range" in params:
            command.extend(["--exit-period-range", params["exit_range"]])
        if "atr_range" in params:
            command.extend(["--atr-period-range", params["atr_range"]])
    else:  # ema
        if "fast_ema_range" in params:
            command.extend(["--fast-ema-range", params["fast_ema_range"]])
        if "slow_ema_range" in params:
            command.extend(["--slow-ema-range", params["slow_ema_range"]])
        if "signal_ema_range" in params:
            command.extend(["--signal-ema-range", params["signal_ema_range"]])

    # Voer commando uit
    return run_command(command, output_callback)


def create_candlestick_chart(
    df: pd.DataFrame,
    title: str = "Price Chart",
    volume: bool = True,
    indicators: Optional[Optional[Optional[Dict[str, Any]]]] = None
) -> go.Figure:
    """Creëer een candlestick chart met Plotly."""

    if df is None or len(df) == 0:
        # Maak een lege figuur met melding
        fig = go.Figure()
        fig.update_layout(
            title="Geen data beschikbaar",
            annotations=[
                dict(
                    text="Er is geen data beschikbaar om weer te geven.",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5
                )
            ]
        )
        return fig

    # Bepaal subplot configuratie
    if volume and "tick_volume" in df.columns:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=("Prijs", "Volume"),
            row_heights=[0.8, 0.2]
        )
    else:
        fig = make_subplots(rows=1, cols=1, subplot_titles=("Prijs",))

    # Voeg candlesticks toe
    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Prijs",
            increasing_line_color='#26a69a',  # Groen voor stijgende candles
            decreasing_line_color='#ef5350',  # Rood voor dalende candles
        ),
        row=1, col=1
    )

    # Voeg volume toe indien gewenst
    if volume and "tick_volume" in df.columns:
        colors = ['#26a69a' if row['close'] >= row['open'] else '#ef5350' for
                  _, row in df.iterrows()]

        fig.add_trace(
            go.Bar(
                x=df["time"],
                y=df["tick_volume"],
                name="Volume",
                marker_color=colors,
                opacity=0.7
            ),
            row=2, col=1
        )

    # Voeg indicators toe indien gewenst
    if indicators:
        if indicators.get("show_ema", False):
            ema1 = indicators.get("ema1", 9)
            ema2 = indicators.get("ema2", 21)

            if ema1 > 0:
                ema1_values = df["close"].ewm(span=ema1, adjust=False).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=ema1_values,
                        mode="lines",
                        name=f"EMA {ema1}",
                        line=dict(color="orange", width=1.5),
                    ),
                    row=1, col=1
                )

            if ema2 > 0:
                ema2_values = df["close"].ewm(span=ema2, adjust=False).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=ema2_values,
                        mode="lines",
                        name=f"EMA {ema2}",
                        line=dict(color="purple", width=1.5),
                    ),
                    row=1, col=1
                )

        if indicators.get("show_bb", False):
            # Bereken Bollinger Bands
            window = 20
            rolling_mean = df["close"].rolling(window=window).mean()
            rolling_std = df["close"].rolling(window=window).std()

            upper_band = rolling_mean + (rolling_std * 2)
            middle_band = rolling_mean
            lower_band = rolling_mean - (rolling_std * 2)

            # Voeg Bollinger Bands toe
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=upper_band,
                    mode="lines",
                    name="Upper BB",
                    line=dict(color="rgba(0, 128, 255, 0.5)", width=1),
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=middle_band,
                    mode="lines",
                    name="Middle BB",
                    line=dict(color="rgba(0, 128, 255, 0.3)", width=1),
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=lower_band,
                    mode="lines",
                    name="Lower BB",
                    line=dict(color="rgba(0, 128, 255, 0.5)", width=1),
                ),
                row=1, col=1
            )

    # Layout aanpassen
    fig.update_layout(
        title=title,
        xaxis_title="Datum",
        yaxis_title="Prijs",
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_white",  # Schoner template
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Y-axis formatter voor volume
    if volume:
        fig.update_yaxes(title_text="Volume", row=2, col=1)

    # Tooltip verbeteringen
    fig.update_traces(
        xhoverformat="%d %b %Y %H:%M",
        yhoverformat=".5f"
    )

    return fig


def create_performance_chart(result: Dict[str, Any]) -> go.Figure:
    """Creëer een grafiek met prestatie-overzicht."""
    if not result:
        # Lege figuur
        fig = go.Figure()
        fig.update_layout(title="Geen resultaten beschikbaar")
        return fig

    # Prestatiedata
    metrics = [
        {"name": "Rendement %", "value": result["return"]},
        {"name": "Sharpe Ratio", "value": result["sharpe"]},
        {"name": "Max Drawdown %", "value": result["drawdown"]},
    ]

    if result.get("win_rate"):
        metrics.append({"name": "Win Rate %", "value": result["win_rate"]})

    if result.get("profit_factor"):
        metrics.append(
            {"name": "Profit Factor", "value": result["profit_factor"]})

    # Kleuren bepalen
    colors = []

    for metric in metrics:
        name = metric["name"]
        value = metric["value"]

        if name == "Max Drawdown %":
            # Drawdown is negative, so invert colors
            if value < 5:
                colors.append("#4CAF50")  # Green
            elif value < 10:
                colors.append("#FFC107")  # Amber
            else:
                colors.append("#F44336")  # Red

        elif name in ["Rendement %", "Win Rate %"]:
            if value > 15:
                colors.append("#4CAF50")  # Green
            elif value > 5:
                colors.append("#8BC34A")  # Light Green
            elif value > 0:
                colors.append("#FFC107")  # Amber
            else:
                colors.append("#F44336")  # Red

        elif name == "Sharpe Ratio":
            if value > 1.5:
                colors.append("#4CAF50")  # Green
            elif value > 1:
                colors.append("#8BC34A")  # Light Green
            elif value > 0:
                colors.append("#FFC107")  # Amber
            else:
                colors.append("#F44336")  # Red

        elif name == "Profit Factor":
            if value > 1.5:
                colors.append("#4CAF50")  # Green
            elif value > 1:
                colors.append("#8BC34A")  # Light Green
            else:
                colors.append("#F44336")  # Red

        else:
            colors.append("#2196F3")  # Default blue

    # Maak bar chart
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=[m["name"] for m in metrics],
            y=[m["value"] for m in metrics],
            marker_color=colors,
            text=[f"{m['value']:.2f}" for m in metrics],
            textposition="auto",
        )
    )

    # Layout
    title = f"Prestatie Overzicht: {result['strategy']} op {result['symbol']}"
    if result.get("timeframe"):
        title += f" ({result['timeframe']})"

    fig.update_layout(
        title=title,
        xaxis_title="Metric",
        yaxis_title="Waarde",
        height=400,
        template="plotly_white",
    )

    return fig


def validate_symbol(symbol: str) -> bool:
    """Valideer een handelssymbool."""
    return symbol.upper() in VALID_SYMBOLS


def validate_symbols(symbols_str: str) -> Tuple[bool, List[str]]:
    """Valideer een lijst van symbolen."""
    if not symbols_str:
        return False, []

    symbols = [s.strip().upper() for s in symbols_str.split(",")]
    valid = all(s in VALID_SYMBOLS for s in symbols)

    return valid, symbols


# -- UI Componenten --

def render_sidebar() -> None:
    """Render de sidebar met navigatie en info."""
    st.sidebar.title("Sophia Trading Framework")

    # Versie info en import status
    if SOPHIA_IMPORTS_SUCCESS:
        st.sidebar.success("✅ Framework succesvol geladen")
    else:
        st.sidebar.error(f"❌ Framework imports mislukt: {import_error}")

    # Navigatie
    st.sidebar.subheader("Navigatie")
    selected_tab = st.sidebar.radio(
        "Ga naar:",
        options=["Backtesting", "Optimalisatie", "Datavisualisatie"],
        index=["Backtesting", "Optimalisatie", "Datavisualisatie"].index(
            st.session_state.active_tab),
        key="navigation"
    )

    # Update de actieve tab in sessie state
    if selected_tab != st.session_state.active_tab:
        st.session_state.active_tab = selected_tab
        st.rerun()

    # Recente resultaten in sidebar
    st.sidebar.markdown("---")
    with st.sidebar.expander("📊 Recente Resultaten", expanded=False):
        backtest_results = load_backtest_results()
        optimize_results = load_optimization_results()

        all_results = backtest_results + optimize_results
        all_results.sort(key=lambda x: x["date"], reverse=True)

        if all_results:
            # Maak tabs voor backtest en optimalisatie resultaten
            result_tabs = st.tabs(["Alle", "Backtest", "Optimalisatie"])

            # Tab 1: Alle resultaten
            with result_tabs[0]:
                for i, result in enumerate(all_results[:5]):
                    st.markdown(
                        f"**{result['date']} - {result['strategy']} {result['type']}**")
                    st.markdown(
                        f"{result['symbol']} | Return: {result['return']:.2f}% | Sharpe: {result['sharpe']:.2f}")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("🔍 Details", key=f"view_all_{i}"):
                            # Set last result based on type
                            if result["type"] == "backtest":
                                st.session_state.last_backtest_result = result
                                st.session_state.active_tab = "Backtesting"
                            else:
                                st.session_state.last_optimize_result = result
                                st.session_state.active_tab = "Optimalisatie"
                            st.rerun()

                    st.markdown("---")

            # Tab 2: Backtest resultaten
            with result_tabs[1]:
                if backtest_results:
                    for i, result in enumerate(backtest_results[:5]):
                        st.markdown(
                            f"**{result['date']} - {result['strategy']}**")
                        st.markdown(
                            f"{result['symbol']} | Return: {result['return']:.2f}% | Trades: {result['trades']}")

                        if st.button("🔍 Bekijk", key=f"view_bt_{i}"):
                            st.session_state.last_backtest_result = result
                            st.session_state.active_tab = "Backtesting"
                            st.rerun()

                        st.markdown("---")
                else:
                    st.info("Geen backtest resultaten gevonden")

            # Tab 3: Optimalisatie resultaten
            with result_tabs[2]:
                if optimize_results:
                    for i, result in enumerate(optimize_results[:5]):
                        st.markdown(
                            f"**{result['date']} - {result['strategy']}**")
                        st.markdown(
                            f"{result['symbol']} | Metric: {result['metric']} | Comb: {result['combinations']}")

                        if st.button("🔍 Bekijk", key=f"view_opt_{i}"):
                            st.session_state.last_optimize_result = result
                            st.session_state.active_tab = "Optimalisatie"
                            st.rerun()

                        st.markdown("---")
                else:
                    st.info("Geen optimalisatie resultaten gevonden")
        else:
            st.info(
                "Geen resultaten gevonden. Voer eerst een backtest of optimalisatie uit.")

    # MT5 status
    st.sidebar.markdown("---")
    with st.sidebar.expander("🔌 MetaTrader 5 Status", expanded=False):
        mt5_config = load_config().get("mt5", {})

        if mt5_config:
            st.markdown(
                f"**Server:** {mt5_config.get('server', 'Niet geconfigureerd')}")
            st.markdown(
                f"**Login:** {mt5_config.get('login', 'Niet geconfigureerd')}")
            st.markdown(
                f"**Pad:** {mt5_config.get('mt5_path', 'Niet geconfigureerd')}")

            # Test verbinding knop
            if st.button("🔄 Test Verbinding"):
                try:
                    if SOPHIA_IMPORTS_SUCCESS:
                        connector = MT5Connector(mt5_config)
                        if connector.connect():
                            account_info = connector.get_account_info()
                            connector.disconnect()

                            if account_info:
                                st.success("✅ Verbinding succesvol!")
                                st.markdown(
                                    f"**Balans:** {account_info.get('balance', 0)} {account_info.get('currency', '')}")
                            else:
                                st.warning(
                                    "⚠️ Verbonden, maar kon geen account info ophalen.")
                        else:
                            st.error("❌ Kon geen verbinding maken met MT5.")
                    else:
                        st.error("❌ MT5Connector niet beschikbaar.")
                except Exception as e:
                    st.error(f"❌ Fout bij verbinden: {e}")
        else:
            st.info(
                "MetaTrader 5 is niet geconfigureerd. Configureer in settings.json.")

            # Velden voor het configureren
            with st.form("mt5_config_form"):
                new_server = st.text_input("Server", "FTMO-Demo2")
                new_login = st.text_input("Login")
                new_password = st.text_input("Password", type="password")
                new_path = st.text_input("MT5 Pad",
                                         "C:\\Program Files\\MetaTrader 5\\terminal64.exe")

                if st.form_submit_button("💾 Opslaan"):
                    config = load_config()
                    config["mt5"] = {
                        "server": new_server,
                        "login": int(new_login) if new_login.isdigit() else 0,
                        "password": new_password,
                        "mt5_path": new_path
                    }

                    if save_config(config):
                        st.success("✅ MT5 configuratie opgeslagen!")
                    else:
                        st.error("❌ Kon configuratie niet opslaan.")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("Sophia Trading Framework v2.0")

    # Debug mode toggle
    debug = st.sidebar.checkbox("Debug Mode", value=st.session_state.show_debug)
    if debug != st.session_state.show_debug:
        st.session_state.show_debug = debug
        st.rerun()


def render_backtest_tab() -> None:
    """Render het backtesting tabblad."""
    st.header("🧪 Backtesting")

    # Laad profielen voor later gebruik
    profiles = load_profiles()
    st.session_state.profiles = profiles

    # Structuur: 2 kolommen - configuratie links, resultaten/output rechts
    col1, col2 = st.columns([3, 2])

    with col1:
        with st.form("backtest_form"):
            st.subheader("Strategie Configuratie")

            # Strategie selectie
            strategy = st.selectbox(
                "Selecteer Strategie",
                options=["turtle", "ema"],
                index=0 if st.session_state.backtest_params[
                               "strategy"] == "turtle" else 1,
                help="Kies een trading strategie om te testen"
            )

            # Strategie-specifieke parameters
            if strategy == "turtle":
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    entry_period = st.number_input(
                        "Entry Period",
                        min_value=5,
                        max_value=50,
                        value=st.session_state.backtest_params.get(
                            "entry_period", 20),
                        help="Periode voor entry Donchian channel (hoger = minder signalen)"
                    )
                with col_t2:
                    exit_period = st.number_input(
                        "Exit Period",
                        min_value=3,
                        max_value=30,
                        value=st.session_state.backtest_params.get(
                            "exit_period", 10),
                        help="Periode voor exit Donchian channel (moet lager zijn dan entry)"
                    )
                with col_t3:
                    atr_period = st.number_input(
                        "ATR Period",
                        min_value=5,
                        max_value=30,
                        value=st.session_state.backtest_params.get("atr_period",
                                                                   14),
                        help="Periode voor Average True Range berekening"
                    )
                vol_filter = st.checkbox(
                    "Gebruik Volatiliteitsfilter",
                    value=st.session_state.backtest_params.get("vol_filter",
                                                               True),
                    help="Filter trades op basis van marktvolatiliteit"
                )
            else:  # EMA strategie
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    fast_ema = st.number_input(
                        "Fast EMA",
                        min_value=3,
                        max_value=25,
                        value=st.session_state.backtest_params.get("fast_ema",
                                                                   9),
                        help="Periode voor snelle EMA (korte termijn trend)"
                    )
                    signal_ema = st.number_input(
                        "Signal EMA",
                        min_value=2,
                        max_value=15,
                        value=st.session_state.backtest_params.get("signal_ema",
                                                                   5),
                        help="Periode voor MACD signaal lijn"
                    )
                with col_e2:
                    slow_ema = st.number_input(
                        "Slow EMA",
                        min_value=10,
                        max_value=50,
                        value=st.session_state.backtest_params.get("slow_ema",
                                                                   21),
                        help="Periode voor trage EMA (lange termijn trend)"
                    )
                    rsi_period = st.number_input(
                        "RSI Period",
                        min_value=5,
                        max_value=30,
                        value=st.session_state.backtest_params.get("rsi_period",
                                                                   14),
                        help="Periode voor RSI indicator"
                    )

            # Horizontale lijn
            st.markdown("---")

            # Algemene parameters
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                symbols = st.text_input(
                    "Symbolen (kommagescheiden)",
                    value=st.session_state.backtest_params.get("symbols",
                                                               "EURUSD"),
                    help="Eén of meer symbolen, gescheiden door komma's"
                )

                # Valideer symbolen
                valid, symbol_list = validate_symbols(symbols)
                if not valid and symbols:
                    st.warning(
                        f"Let op: Onbekende symbolen. Geldige symbolen zijn: {', '.join(VALID_SYMBOLS)}")

            with col_g2:
                timeframe = st.selectbox(
                    "Timeframe",
                    options=VALID_TIMEFRAMES,
                    index=VALID_TIMEFRAMES.index(
                        st.session_state.backtest_params.get("timeframe",
                                                             "H4")),
                    help="Tijdsinterval voor de prijsdata"
                )

            # Test periode & kapitaal
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                period = st.selectbox(
                    "Test Periode",
                    options=["1m", "3m", "6m", "1y", "2y", "5y"],
                    index=["1m", "3m", "6m", "1y", "2y", "5y"].index(
                        st.session_state.backtest_params.get("period", "1y")),
                    help="Hoeveel historische data gebruiken voor de test"
                )
            with col_p2:
                initial_cash = st.number_input(
                    "Startkapitaal ($)",
                    min_value=1000,
                    max_value=1000000,
                    value=int(
                        st.session_state.backtest_params.get("initial_cash",
                                                             10000)),
                    step=1000,
                    help="Beginkapitaal voor de backtest"
                )

            # Output opties
            plot_results = st.checkbox(
                "Toon Grafiek in Resultaten",
                value=st.session_state.backtest_params.get("plot", True),
                help="Genereer een equity-curve grafiek"
            )

            # Submit button
            submit_button = st.form_submit_button(
                "🚀 Start Backtest",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.running_process
            )

            # Wanneer form submit: update parameters en start backtest
            if submit_button:
                # Verzamel parameters
                updated_params = {
                    "strategy": strategy,
                    "symbols": symbols,
                    "timeframe": timeframe,
                    "period": period,
                    "initial_cash": initial_cash,
                    "plot": plot_results,
                }

                if strategy == "turtle":
                    updated_params.update({
                        "entry_period": entry_period,
                        "exit_period": exit_period,
                        "atr_period": atr_period,
                        "vol_filter": vol_filter,
                    })
                else:  # ema
                    updated_params.update({
                        "fast_ema": fast_ema,
                        "slow_ema": slow_ema,
                        "signal_ema": signal_ema,
                        "rsi_period": rsi_period,
                    })

                # Update sessie state
                st.session_state.backtest_params.update(updated_params)
                st.session_state.running_process = True
                st.session_state.output_lines = []
                st.session_state.last_run_id = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # Start backtest
                def output_callback(line) -> None:
                    st.session_state.output_lines.append(line)

                try:
                    with st.spinner("Backtest uitvoeren..."):
                        returncode, _ = run_backtest(
                            st.session_state.backtest_params, output_callback)

                    st.session_state.running_process = False

                    if returncode == 0:
                        st.success("✅ Backtest succesvol voltooid!")
                        # Laad recente resultaten
                        results = load_backtest_results()
                        if results:
                            st.session_state.last_backtest_result = results[0]
                    else:
                        st.error("❌ Backtest mislukt!")
                except Exception as e:
                    st.session_state.running_process = False
                    st.error(f"❌ Fout bij uitvoeren backtest: {e}")

                # Herteken het formulier
                st.rerun()

        # Profiel management
        with st.expander("💾 Profiel Management", expanded=False):
            st.markdown(
                "Sla huidige instellingen op als profiel of laad een bestaand profiel.")

            # Profiel opslaan
            col_save1, col_save2 = st.columns([3, 1])
            with col_save1:
                profile_name = st.text_input("Profiel Naam",
                                             key="backtest_profile_name")
            with col_save2:
                if st.button("💾 Opslaan", use_container_width=True,
                             disabled=not profile_name):
                    if save_profile(profile_name,
                                    st.session_state.backtest_params):
                        st.success(f"✅ Profiel '{profile_name}' opgeslagen!")
                        # Herlaad profielen
                        st.session_state.profiles = load_profiles()
                        st.rerun()
                    else:
                        st.error("❌ Kon profiel niet opslaan")

            # Profielen weergeven
            if profiles:
                st.markdown("### Opgeslagen Profielen")

                # Maak een selectbox voor profielen
                profile_options = [p["name"] for p in profiles]
                selected_profile = st.selectbox(
                    "Selecteer een profiel",
                    options=profile_options,
                    key="backtest_profile_select"
                )

                # Vind geselecteerd profiel
                selected_profile_data = next(
                    (p for p in profiles if p["name"] == selected_profile),
                    None)

                if selected_profile_data:
                    # Toon info
                    st.markdown(
                        f"**Strategie:** {selected_profile_data['strategy']}")
                    st.markdown(
                        f"**Symbolen:** {selected_profile_data['symbols']}")
                    st.markdown(
                        f"**Timeframe:** {selected_profile_data['timeframe']}")

                    # Laad & verwijder knoppen
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if st.button("📂 Laden", use_container_width=True,
                                     key="load_backtest_profile"):
                            # Laad profiel in huidige parameters
                            st.session_state.backtest_params.update(
                                selected_profile_data["data"])
                            st.success(
                                f"✅ Profiel '{selected_profile}' geladen!")
                            st.rerun()

                    with col_act2:
                        if st.button("🗑️ Verwijderen", use_container_width=True,
                                     key="delete_backtest_profile"):
                            try:
                                os.remove(selected_profile_data["filepath"])
                                st.success(
                                    f"✅ Profiel '{selected_profile}' verwijderd!")
                                # Herlaad profielen
                                st.session_state.profiles = load_profiles()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Kon profiel niet verwijderen: {e}")
            else:
                st.info("Geen opgeslagen profielen gevonden")

    # Rechterkolom: Uitvoer en resultaten
    with col2:
        # Als er een proces loopt, toon live output
        if st.session_state.running_process:
            st.subheader("⚙️ Backtest Uitvoering")
            output_area = st.empty()

            if st.session_state.output_lines:
                output_area.text('\n'.join(st.session_state.output_lines[-20:]))

        # Als er recente output is maar geen proces loopt, toon uitklapbare output
        elif st.session_state.output_lines:
            with st.expander("📋 Uitvoerlogboek", expanded=False):
                full_output = '\n'.join(st.session_state.output_lines)
                st.text_area("Output", value=full_output, height=300)

        # Als er een resultaat is, toon het
        if st.session_state.last_backtest_result:
            result = st.session_state.last_backtest_result
            st.subheader("📊 Backtest Resultaten")

            # Metrics in boxes
            col_m1, col_m2 = st.columns(2)
            col_m3, col_m4 = st.columns(2)

            with col_m1:
                st.metric("Rendement", f"{result['return']:.2f}%")
            with col_m2:
                st.metric("Sharpe Ratio", f"{result['sharpe']:.2f}")
            with col_m3:
                st.metric("Max Drawdown", f"{result['drawdown']:.2f}%")
            with col_m4:
                st.metric("Aantal Trades", str(result['trades']))

            # Performance chart
            perf_chart = create_performance_chart(result)
            st.plotly_chart(perf_chart, use_container_width=True)

            # Details bekijken
            with st.expander("📈 Gedetailleerde Resultaten", expanded=False):
                # Resultaat details
                strategy_params = result.get("raw_data", {}).get("parameters",
                                                                 {}).get(
                    "strategy_params", {})
                if strategy_params:
                    st.markdown("### Strategie Parameters")
                    st.json(strategy_params)

                # Metrics details
                metrics = result.get("raw_data", {}).get("metrics", {})
                if metrics:
                    st.markdown("### Performance Metrics")

                    # Maak een nette tabel van metrics
                    metrics_df = pd.DataFrame([{
                        "Metric": k.replace("_", " ").title(),
                        "Waarde": f"{v:.4f}" if isinstance(v, (
                            float, int)) else str(v)
                    } for k, v in metrics.items()])

                    st.dataframe(metrics_df, use_container_width=True)

                # Trades details
                trades = result.get("raw_data", {}).get("trades", [])
                if trades:
                    st.markdown("### Handelsresultaten")
                    trades_df = pd.DataFrame(trades)
                    st.dataframe(trades_df, use_container_width=True)

                # Toon plot als beschikbaar
                if result.get("has_plot", False) and result.get("plot_path"):
                    try:
                        st.markdown("### Equity Curve")
                        st.image(result["plot_path"])
                    except Exception as e:
                        st.error(f"Kon grafiek niet laden: {e}")

            # Nieuwe backtest knop
            if st.button("🔄 Nieuwe Backtest", use_container_width=True):
                st.session_state.last_backtest_result = None
                st.rerun()

        # Als geen resultaat maar wel debug mode, toon debug info
        elif st.session_state.show_debug:
            st.subheader("🐞 Debug Informatie")

            # Directory status
            st.markdown("### Directory Status")
            status_info = {
                "Backtest Results": str(BACKTEST_RESULTS_DIR),
                "# JSON Files": len(list(BACKTEST_RESULTS_DIR.glob("*.json"))),
                "# PNG Files": len(list(BACKTEST_RESULTS_DIR.glob("*.png"))),
                "Project Root": str(project_root),
                "Python Path": str(sys.path[0]),
            }

            for key, value in status_info.items():
                st.markdown(f"**{key}:** {value}")

            # Toon alle beschikbare bestanden
            with st.expander("Bekijk Bestanden", expanded=False):
                for file in BACKTEST_RESULTS_DIR.glob("*.json"):
                    if st.button(f"Bekijk {file.name}",
                                 key=f"view_debug_{file.name}"):
                        try:
                            with open(file, "r") as f:
                                content = json.load(f)
                            st.json(content)
                        except Exception as e:
                            st.error(f"Fout bij laden bestand: {e}")


def render_optimization_tab() -> None:
    """Render het optimalisatie tabblad."""
    st.header("⚙️ Parameter Optimalisatie")

    # Structuur: 2 kolommen
    col1, col2 = st.columns([3, 2])

    with col1:
        with st.form("optimize_form"):
            st.subheader("Optimalisatie Configuratie")

            # Strategie selectie
            strategy = st.selectbox(
                "Selecteer Strategie",
                options=["turtle", "ema"],
                index=0 if st.session_state.optimize_params[
                               "strategy"] == "turtle" else 1,
                help="Kies een trading strategie om te optimaliseren"
            )

            # Strategie-specifieke parameter ranges
            if strategy == "turtle":
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    entry_range = st.text_input(
                        "Entry Period Bereik",
                        value=st.session_state.optimize_params.get(
                            "entry_range", "10,20,30,40"),
                        help="Kommagescheiden waarden voor entry period"
                    )
                with col_t2:
                    exit_range = st.text_input(
                        "Exit Period Bereik",
                        value=st.session_state.optimize_params.get("exit_range",
                                                                   "5,10,15,20"),
                        help="Kommagescheiden waarden voor exit period"
                    )
                with col_t3:
                    atr_range = st.text_input(
                        "ATR Period Bereik",
                        value=st.session_state.optimize_params.get("atr_range",
                                                                   "10,14,20"),
                        help="Kommagescheiden waarden voor ATR period"
                    )
            else:  # EMA strategie
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    fast_ema_range = st.text_input(
                        "Fast EMA Bereik",
                        value=st.session_state.optimize_params.get(
                            "fast_ema_range", "5,9,12,15"),
                        help="Kommagescheiden waarden voor fast EMA period"
                    )
                with col_e2:
                    slow_ema_range = st.text_input(
                        "Slow EMA Bereik",
                        value=st.session_state.optimize_params.get(
                            "slow_ema_range", "20,25,30"),
                        help="Kommagescheiden waarden voor slow EMA period"
                    )
                with col_e3:
                    signal_ema_range = st.text_input(
                        "Signal EMA Bereik",
                        value=st.session_state.optimize_params.get(
                            "signal_ema_range", "5,7,9"),
                        help="Kommagescheiden waarden voor signal EMA period"
                    )

            # Horizontale lijn
            st.markdown("---")

            # Algemene parameters
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                symbols = st.text_input(
                    "Symbolen (kommagescheiden)",
                    value=st.session_state.optimize_params.get("symbols",
                                                               "EURUSD"),
                    help="Eén of meer symbolen, gescheiden door komma's"
                )

                # Valideer symbolen
                valid, symbol_list = validate_symbols(symbols)
                if not valid and symbols:
                    st.warning(
                        f"Let op: Onbekende symbolen. Geldige symbolen zijn: {', '.join(VALID_SYMBOLS)}")

            with col_g2:
                timeframe = st.selectbox(
                    "Timeframe",
                    options=VALID_TIMEFRAMES,
                    index=VALID_TIMEFRAMES.index(
                        st.session_state.optimize_params.get("timeframe",
                                                             "H4")),
                    help="Tijdsinterval voor de prijsdata"
                )

            # Test periode & metric
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                period = st.selectbox(
                    "Test Periode",
                    options=["1m", "3m", "6m", "1y", "2y", "5y"],
                    index=["1m", "3m", "6m", "1y", "2y", "5y"].index(
                        st.session_state.optimize_params.get("period", "1y")),
                    help="Hoeveel historische data gebruiken voor de test"
                )
            with col_p2:
                metric = st.selectbox(
                    "Optimalisatie Metric",
                    options=["sharpe", "return", "drawdown", "profit_factor"],
                    index=["sharpe", "return", "drawdown",
                           "profit_factor"].index(
                        st.session_state.optimize_params.get("metric",
                                                             "sharpe")),
                    help="Welke metric te maximaliseren (of minimaliseren voor drawdown)"
                )

            # Maximum aantal combinaties
            max_combinations = st.slider(
                "Maximum Aantal Combinaties",
                min_value=10,
                max_value=500,
                value=st.session_state.optimize_params.get("max_combinations",
                                                           50),
                step=10,
                help="Hoeveel parametercombinaties maximaal testen"
            )

            # Submit button
            submit_button = st.form_submit_button(
                "🚀 Start Optimalisatie",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.running_process
            )

            # Wanneer form submit: update parameters en start optimalisatie
            if submit_button:
                # Verzamel parameters
                updated_params = {
                    "strategy": strategy,
                    "symbols": symbols,
                    "timeframe": timeframe,
                    "period": period,
                    "metric": metric,
                    "max_combinations": max_combinations,
                }

                if strategy == "turtle":
                    updated_params.update({
                        "entry_range": entry_range,
                        "exit_range": exit_range,
                        "atr_range": atr_range,
                    })
                else:  # ema
                    updated_params.update({
                        "fast_ema_range": fast_ema_range,
                        "slow_ema_range": slow_ema_range,
                        "signal_ema_range": signal_ema_range,
                    })

                # Update sessie state
                st.session_state.optimize_params.update(updated_params)
                st.session_state.running_process = True
                st.session_state.output_lines = []
                st.session_state.last_run_id = f"optimize_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # Start optimalisatie
                def output_callback(line) -> None:
                    st.session_state.output_lines.append(line)

                try:
                    with st.spinner("Optimalisatie uitvoeren..."):
                        returncode, _ = run_optimization(
                            st.session_state.optimize_params, output_callback)

                    st.session_state.running_process = False

                    if returncode == 0:
                        st.success("✅ Optimalisatie succesvol voltooid!")
                        # Laad recente resultaten
                        results = load_optimization_results()
                        if results:
                            st.session_state.last_optimize_result = results[0]
                    else:
                        st.error("❌ Optimalisatie mislukt!")
                except Exception as e:
                    st.session_state.running_process = False
                    st.error(f"❌ Fout bij uitvoeren optimalisatie: {e}")

                # Herteken het formulier
                st.rerun()

    # Rechterkolom: Uitvoer en resultaten
    with col2:
        # Als er een proces loopt, toon live output
        if st.session_state.running_process:
            st.subheader("⚙️ Optimalisatie Uitvoering")
            output_area = st.empty()

            if st.session_state.output_lines:
                output_area.text('\n'.join(st.session_state.output_lines[-20:]))

        # Als er recente output is maar geen proces loopt, toon uitklapbare output
        elif st.session_state.output_lines:
            with st.expander("📋 Uitvoerlogboek", expanded=False):
                full_output = '\n'.join(st.session_state.output_lines)
                st.text_area("Output", value=full_output, height=300)

        # Als er een resultaat is, toon het
        if st.session_state.last_optimize_result:
            result = st.session_state.last_optimize_result
            st.subheader("📊 Optimalisatie Resultaten")

            # Beste parameters en metric
            st.markdown(f"**Strategie:** {result['strategy']}")
            st.markdown(f"**Optimalisatie Metric:** {result['metric']}")
            st.markdown(f"**Geteste Combinaties:** {result['combinations']}")

            # Beste parameters in een tabel
            st.markdown("### Beste Parameters")

            best_params = result.get("best_params", {})
            if best_params:
                # Maak een nette tabel van parameters
                params_df = pd.DataFrame([{
                    "Parameter": k.replace("_", " ").title(),
                    "Waarde": v
                } for k, v in best_params.items()])

                st.dataframe(params_df, use_container_width=True)

                # Knop om parameters in backtest te gebruiken
                if st.button("⚡ Gebruik deze parameters voor backtest",
                             use_container_width=True):
                    # Update backtest parameters met beste parameters uit optimalisatie
                    new_params = st.session_state.backtest_params.copy()
                    new_params["strategy"] = result["strategy"]

                    # Voeg alle beste parameters toe (met correcte naam)
                    for k, v in best_params.items():
                        new_params[k] = v

                    st.session_state.backtest_params = new_params
                    st.session_state.active_tab = "Backtesting"
                    st.success("✅ Parameters overgenomen naar backtest tab!")
                    st.rerun()

            # Toon top resultaten als beschikbaar
            top_results = result.get("raw_data", {}).get("results", [])
            if top_results:
                with st.expander("🏆 Top Resultaten", expanded=True):
                    st.markdown("### Top 10 Parameter Combinaties")

                    # Maak een tabel van de top resultaten
                    top_data = []

                    for i, res in enumerate(top_results[:10]):
                        params = res.get("params", {})
                        metrics = res.get("metrics", {})

                        # Parameter string maken
                        if result["strategy"] == "turtle":
                            params_str = f"E{params.get('entry_period', '-')}/X{params.get('exit_period', '-')}/A{params.get('atr_period', '-')}"
                        else:  # ema
                            params_str = f"F{params.get('fast_ema', '-')}/S{params.get('slow_ema', '-')}/G{params.get('signal_ema', '-')}"

                        top_data.append({
                            "Rank": i + 1,
                            "Parameters": params_str,
                            "Return %": f"{metrics.get('total_return_pct', 0):.2f}",
                            "Sharpe": f"{metrics.get('sharpe_ratio', 0):.2f}",
                            "Drawdown %": f"{metrics.get('max_drawdown_pct', 0):.2f}",
                            "Trades": metrics.get("total_trades", 0)
                        })

                    # Toon als dataframe
                    top_df = pd.DataFrame(top_data)
                    st.dataframe(top_df, use_container_width=True)

                    # Visualisatie van top resultaten
                    st.markdown("### Performance Vergelijking")

                    # Prestatiemetrics voor top 5
                    metrics_data = []
                    for i, res in enumerate(top_results[:5]):
                        metrics = res.get("metrics", {})
                        metrics_data.append({
                            "Rank": i + 1,
                            "Return": metrics.get("total_return_pct", 0),
                            "Sharpe": metrics.get("sharpe_ratio", 0),
                            "Drawdown": metrics.get("max_drawdown_pct", 0),
                        })

                    metrics_df = pd.DataFrame(metrics_data)

                    # Maak grafieken met altair
                    base = alt.Chart(metrics_df).encode(x="Rank:O")

                    return_bars = base.mark_bar().encode(
                        y=alt.Y("Return:Q", title="Return %"),
                        color=alt.Color("Return:Q",
                                        scale=alt.Scale(scheme="blueorange"))
                    )

                    sharpe_bars = base.mark_bar().encode(
                        y=alt.Y("Sharpe:Q", title="Sharpe Ratio"),
                        color=alt.Color("Sharpe:Q",
                                        scale=alt.Scale(scheme="blueorange"))
                    )

                    drawdown_bars = base.mark_bar().encode(
                        y=alt.Y("Drawdown:Q", title="Drawdown %"),
                        color=alt.Color("Drawdown:Q",
                                        scale=alt.Scale(scheme="orangered"))
                    )

                    # Visualiseer de grafieken
                    chart = alt.hconcat(return_bars, sharpe_bars,
                                        drawdown_bars).resolve_scale(
                        color='independent'
                    )

                    st.altair_chart(chart, use_container_width=True)

            # Toon plot als beschikbaar
            if result.get("has_plot", False) and result.get("plot_path"):
                try:
                    with st.expander("📈 Optimalisatie Plot", expanded=True):
                        st.image(result["plot_path"])
                except Exception as e:
                    st.error(f"Kon grafiek niet laden: {e}")

            # Nieuwe optimalisatie knop
            if st.button("🔄 Nieuwe Optimalisatie", use_container_width=True):
                st.session_state.last_optimize_result = None
                st.rerun()


def render_datavisualization_tab() -> None:
    """Render het datavisualisatie tabblad."""
    st.header("📊 Marktdata Analyse")

    # Structuur: configuratie boven, visualisatie onder
    col1, col2 = st.columns([2, 1])

    with col1:
        with st.form("data_form"):
            st.subheader("Data Configuratie")

            # Symbool en timeframe
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                symbol = st.selectbox(
                    "Symbool",
                    options=VALID_SYMBOLS,
                    index=VALID_SYMBOLS.index(
                        st.session_state.data_params.get("symbol",
                                                         "EURUSD")) if st.session_state.data_params.get(
                        "symbol") in VALID_SYMBOLS else 0,
                    help="Trading instrument om te analyseren"
                )

            with col_s2:
                timeframe = st.selectbox(
                    "Timeframe",
                    options=VALID_TIMEFRAMES,
                    index=VALID_TIMEFRAMES.index(
                        st.session_state.data_params.get("timeframe", "H4")),
                    help="Tijdsinterval voor de prijsdata"
                )

            # Datumbereik
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                from_date = st.date_input(
                    "Vanaf",
                    value=datetime.strptime(
                        st.session_state.data_params.get("from_date",
                                                         "2024-01-01"),
                        "%Y-%m-%d").date(),
                    help="Startdatum voor data"
                )
            with col_d2:
                to_date = st.date_input(
                    "Tot",
                    value=datetime.strptime(
                        st.session_state.data_params.get("to_date",
                                                         datetime.now().strftime(
                                                             "%Y-%m-%d")),
                        "%Y-%m-%d").date(),
                    help="Einddatum voor data"
                )

            # Indicator opties
            st.markdown("### Indicators")

            # Schakel indicators aan/uit
            col_i1, col_i2, col_i3 = st.columns(3)
            with col_i1:
                show_volume = st.checkbox(
                    "Toon Volume",
                    value=st.session_state.data_params.get("indicators",
                                                           {}).get(
                        "show_volume", True),
                    help="Toon volumedata onder de prijsgrafiek"
                )
            with col_i2:
                show_ema = st.checkbox(
                    "Toon EMA Lijnen",
                    value=st.session_state.data_params.get("indicators",
                                                           {}).get("show_ema",
                                                                   True),
                    help="Toon Exponential Moving Averages"
                )
            with col_i3:
                show_bb = st.checkbox(
                    "Toon Bollinger Bands",
                    value=st.session_state.data_params.get("indicators",
                                                           {}).get("show_bb",
                                                                   False),
                    help="Toon Bollinger Bands (20,2)"
                )

            # EMA instellingen als EMA is geselecteerd
            if show_ema:
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    ema1 = st.number_input(
                        "EMA 1 Periode",
                        min_value=2,
                        max_value=50,
                        value=st.session_state.data_params.get("indicators",
                                                               {}).get("ema1",
                                                                       9),
                        help="Periode voor eerste EMA"
                    )
                with col_e2:
                    ema2 = st.number_input(
                        "EMA 2 Periode",
                        min_value=2,
                        max_value=100,
                        value=st.session_state.data_params.get("indicators",
                                                               {}).get("ema2",
                                                                       21),
                        help="Periode voor tweede EMA"
                    )
            else:
                ema1 = ema2 = 0

            # Submit button
            submit_button = st.form_submit_button(
                "📊 Genereer Grafiek",
                type="primary",
                use_container_width=True
            )

            # Wanneer form submit: update parameters en genereer grafiek
            if submit_button:
                # Update sessie state
                st.session_state.data_params.update({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "from_date": from_date.strftime("%Y-%m-%d"),
                    "to_date": to_date.strftime("%Y-%m-%d"),
                    "indicators": {
                        "show_volume": show_volume,
                        "show_ema": show_ema,
                        "show_bb": show_bb,
                        "ema1": ema1,
                        "ema2": ema2,
                    }
                })

                # Haal data op
                with st.spinner("Data ophalen..."):
                    df = fetch_mt5_data(
                        symbol,
                        timeframe,
                        from_date.strftime("%Y-%m-%d"),
                        to_date.strftime("%Y-%m-%d")
                    )

                    if df is not None and len(df) > 0:
                        st.session_state.chart_data = df
                        st.success(
                            f"✅ {len(df)} prijspunten succesvol opgehaald")
                    else:
                        st.error("❌ Kon geen data ophalen.")
                        st.session_state.chart_data = None

                # Herteken
                st.rerun()

    with col2:
        # Data statistieken als data beschikbaar is
        if st.session_state.chart_data is not None:
            df = st.session_state.chart_data

            st.subheader("Marktdata Statistieken")

            # Basisstatistieken
            st.markdown(f"**Symbol:** {st.session_state.data_params['symbol']}")
            st.markdown(
                f"**Timeframe:** {st.session_state.data_params['timeframe']}")
            st.markdown(
                f"**Periode:** {st.session_state.data_params['from_date']} tot {st.session_state.data_params['to_date']}")
            st.markdown(f"**Datapunten:** {len(df)}")

            # Prijsstatistieken
            st.markdown("### Prijsstatistieken")

            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("Open", f"{df['open'].iloc[0]:.5f}")
                st.metric("Min", f"{df['low'].min():.5f}")
            with col_stat2:
                st.metric("Last", f"{df['close'].iloc[-1]:.5f}")
                st.metric("Max", f"{df['high'].max():.5f}")

            # Prijsverandering
            first_price = df['close'].iloc[0]
            last_price = df['close'].iloc[-1]
            pct_change = (last_price - first_price) / first_price * 100

            st.metric(
                "Verandering",
                f"{pct_change:.2f}%",
                delta=f"{last_price - first_price:.5f}",
                delta_color="normal"
            )
        else:
            st.info("Genereer een grafiek om statistieken te zien.")

    # Grafiek sectie (volledige breedte)
    if st.session_state.chart_data is not None:
        df = st.session_state.chart_data
        indicators = st.session_state.data_params.get("indicators", {})

        st.subheader("Prijsanalyse")

        title = f"{st.session_state.data_params['symbol']} {st.session_state.data_params['timeframe']} Chart"
        fig = create_candlestick_chart(
            df,
            title=title,
            volume=indicators.get("show_volume", True),
            indicators=indicators
        )

        st.plotly_chart(fig, use_container_width=True)

        # Extra secties voor patroonanalyse, etc.
        with st.expander("📈 Technische Analyse", expanded=False):
            st.markdown("### Bewegingsstatistieken")

            # Bereken dagelijkse beweging
            daily_changes = df['close'].pct_change() * 100
            daily_range = ((df['high'] - df['low']) / df['low']) * 100

            col_a1, col_a2 = st.columns(2)

            with col_a1:
                st.metric("Gem. Dagelijkse Beweging",
                          f"{daily_changes.mean():.2f}%")
                st.metric("Std. Deviatie", f"{daily_changes.std():.2f}%")

            with col_a2:
                st.metric("Gem. Dagelijkse Range", f"{daily_range.mean():.2f}%")
                st.metric("Max Dagelijkse Range", f"{daily_range.max():.2f}%")

            # Histogram van prijsveranderingen
            st.markdown("### Verdeling van Prijsveranderingen")

            hist_chart = alt.Chart(pd.DataFrame(
                {'change': daily_changes.dropna()})).mark_bar().encode(
                alt.X('change:Q', bin=alt.Bin(maxbins=30),
                      title='Dagelijkse Verandering (%)'),
                alt.Y('count()', title='Frequentie'),
                color=alt.condition(
                    alt.datum.change > 0,
                    alt.value('#4CAF50'),  # green for positive
                    alt.value('#F44336')  # red for negative
                )
            ).properties(height=300)

            st.altair_chart(hist_chart, use_container_width=True)


def main() -> None:
    """Hoofdfunctie voor het dashboard."""

    # Render de sidebar
    render_sidebar()

    # Render het juiste tabblad op basis van de actieve tab in sessie state
    if st.session_state.active_tab == "Backtesting":
        render_backtest_tab()
    elif st.session_state.active_tab == "Optimalisatie":
        render_optimization_tab()
    elif st.session_state.active_tab == "Datavisualisatie":
        render_datavisualization_tab()


if __name__ == "__main__":
    main()
