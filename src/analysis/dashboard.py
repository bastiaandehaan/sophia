#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sophia Trading Framework Dashboard
Een Streamlit dashboard voor het beheren van backtests, optimalisatie
en live trading binnen het Sophia Trading Framework.
"""
# BELANGRIJK: set_page_config MOET als allereerste Streamlit commando worden aangeroepen
import streamlit as st

st.set_page_config(
    page_title="Sophia Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Vervolgens de rest van je imports
import os
import sys
import subprocess
import json
import pandas as pd
import numpy as np
import datetime
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from pathlib import Path

# Zorg dat project root in sys.path staat
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(
    os.path.dirname(script_dir))  # Aangepast voor juiste structuur
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Probeer framework modules te importeren
try:
    from src.utils import load_config, save_config
    from src.connector import MT5Connector
    from src.risk import RiskManager
    from src.strategy import TurtleStrategy
    from src.strategy_ema import EMAStrategy
    from src.analysis.backtrader_adapter import BacktraderAdapter

    SOPHIA_IMPORTS_SUCCESS = True
except ImportError as e:
    SOPHIA_IMPORTS_SUCCESS = False
    import_error = str(e)

# 2. Session State Initialisatie
if 'backtest_params' not in st.session_state:
    st.session_state.backtest_params = {
        "strategy": "turtle",
        "symbols": "EURUSD,USDJPY",
        "timeframe": "H4",
        "period": "1y",
        "initial_cash": 10000,
        "plot": True,
        # Turtle parameters
        "entry_period": 20,
        "exit_period": 10,
        "atr_period": 14,
        "vol_filter": True,
        # EMA parameters
        "fast_ema": 9,
        "slow_ema": 21,
        "signal_ema": 5,
        "rsi_period": 14
    }

if 'optimize_params' not in st.session_state:
    st.session_state.optimize_params = {
        "strategy": "turtle",
        "symbols": "EURUSD",
        "timeframe": "H4",
        "period": "1y",
        "metric": "sharpe",
        "max_combinations": 50,
        # Turtle ranges
        "entry_range": "10,20,30,40",
        "exit_range": "5,10,15,20",
        "atr_range": "10,14,20",
        # EMA ranges
        "fast_ema_range": "5,9,12,15",
        "slow_ema_range": "20,25,30",
        "signal_ema_range": "5,7,9"
    }

if 'live_params' not in st.session_state:
    st.session_state.live_params = {
        "connected": False,
        "strategy": "turtle",
        "symbols": "EURUSD,USDJPY",
        "timeframe": "H4",
        "risk": 1.0,
        "interval": 300
    }

if 'data_params' not in st.session_state:
    one_year_ago = (
            datetime.datetime.now() - datetime.timedelta(days=365)).strftime(
        '%Y-%m-%d')
    today = datetime.datetime.now().strftime('%Y-%m-%d')

    st.session_state.data_params = {
        "symbol": "EURUSD",
        "timeframe": "H4",
        "from_date": one_year_ago,
        "to_date": today,
        "chart_type": "candle",
        "show_ema": True,
        "show_bb": False,
        "show_volume": True,
        "ema1": 9,
        "ema2": 21
    }

if 'backtest_output' not in st.session_state:
    st.session_state.backtest_output = []

if 'optimize_output' not in st.session_state:
    st.session_state.optimize_output = []

if 'live_output' not in st.session_state:
    st.session_state.live_output = []

if 'backtest_running' not in st.session_state:
    st.session_state.backtest_running = False

if 'optimize_running' not in st.session_state:
    st.session_state.optimize_running = False

if 'positions' not in st.session_state:
    st.session_state.positions = []

if 'chart_data' not in st.session_state:
    st.session_state.chart_data = None

# Pad configuratie
CONFIG_DIR = os.path.join(project_root, "config")
BACKTEST_RESULTS_DIR = os.path.join(project_root, "backtest_results")
OPTIMIZE_RESULTS_DIR = os.path.join(project_root, "optimization_results")
PROFILE_DIR = os.path.join(project_root, "backtest_profiles")

# Maak directories aan indien ze niet bestaan
for directory in [CONFIG_DIR, BACKTEST_RESULTS_DIR, OPTIMIZE_RESULTS_DIR,
                  PROFILE_DIR]:
    os.makedirs(directory, exist_ok=True)


# 3. API Compatibiliteit helper voor MT5 connector
def fetch_mt5_data(symbol, timeframe, from_date, to_date):
    """Haal data op van MT5 met verbeterde compatibiliteit."""
    try:
        from src.connector import MT5Connector

        # Laad configuratie
        config = load_config()
        connector = MT5Connector(config.get("mt5", {}))

        if connector.connect():
            # Controleer de signature van get_historical_data
            import inspect
            params = inspect.signature(connector.get_historical_data).parameters

            # Pas aanroep aan op basis van beschikbare parameters
            if 'from_date' in params:
                # Nieuwe API met from_date parameter
                df = connector.get_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    from_date=from_date,
                    to_date=to_date
                )
            elif 'bars_count' in params:
                # Oude API met bars_count parameter
                df = connector.get_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    bars_count=1000  # Redelijke default
                )
            else:
                # Fallback optie
                df = connector.get_historical_data(symbol, timeframe)

            connector.disconnect()
            return df

        else:
            st.error("Kon geen verbinding maken met MetaTrader 5")
            return None

    except Exception as e:
        st.warning(f"MT5 data ophalen mislukt: {e}")
        # Genereer demo data als fallback
        return _generate_demo_data(symbol, from_date, to_date)


def _generate_demo_data(symbol, from_date, to_date):
    """Genereer demo data voor visualisatie wanneer MT5 niet beschikbaar is."""
    start_date = pd.to_datetime(from_date)
    end_date = pd.to_datetime(to_date)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    # Genereer realistische data
    np.random.seed(42)
    n = len(date_range)
    base = 1000 if symbol.startswith("USD") else 100

    close = np.random.normal(0, 1, n).cumsum() + base
    high = close + np.random.normal(0, 0.5, n)
    low = close - np.random.normal(0, 0.5, n)
    open_price = low + np.random.normal(0, (high - low) / 2, n)

    df = pd.DataFrame({
        'time': date_range,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'tick_volume': np.random.randint(100, 1000, n)
    })

    return df


# Helper functies
def load_config(config_path: str = None) -> dict:
    """Laad configuratie uit JSON bestand."""
    if config_path is None:
        config_path = os.path.join(CONFIG_DIR, "settings.json")

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.error(f"Fout bij laden configuratie: {e}")
        return {}


def save_config(config: dict, config_path: str = None) -> bool:
    """Sla configuratie op naar JSON bestand."""
    if config_path is None:
        config_path = os.path.join(CONFIG_DIR, "settings.json")

    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Fout bij opslaan configuratie: {e}")
        return False


def load_backtest_results():
    """Laad bestaande backtest resultaten uit de resultaten directory."""
    results = []
    if os.path.exists(BACKTEST_RESULTS_DIR):
        for filename in os.listdir(BACKTEST_RESULTS_DIR):
            if filename.endswith(".json"):
                try:
                    filepath = os.path.join(BACKTEST_RESULTS_DIR, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)

                    # Extract relevante informatie
                    date_str = filename.split("_")[-1].replace(".json", "")
                    try:
                        date = datetime.datetime.strptime(date_str,
                                                          "%Y%m%d_%H%M%S").strftime(
                            "%Y-%m-%d")
                    except:
                        date = "Onbekend"

                    if "parameters" in data:
                        params = data["parameters"]
                        metrics = data["metrics"] if "metrics" in data else {}

                        results.append({
                            "date": date,
                            "type": "backtest",
                            "strategy": params.get("strategy", "unknown"),
                            "symbol": ", ".join(
                                params.get("symbols", ["unknown"])),
                            "timeframe": params.get("timeframe", "unknown"),
                            "return": metrics.get("total_return_pct", 0),
                            "sharpe": metrics.get("sharpe_ratio", 0),
                            "filepath": filepath
                        })
                except Exception as e:
                    print(f"Fout bij laden van {filename}: {e}")

    return sorted(results, key=lambda x: x["date"], reverse=True)


def load_optimization_results():
    """Laad bestaande optimalisatie resultaten uit de resultaten directory."""
    results = []
    if os.path.exists(OPTIMIZE_RESULTS_DIR):
        for filename in os.listdir(OPTIMIZE_RESULTS_DIR):
            if filename.endswith(".json"):
                try:
                    filepath = os.path.join(OPTIMIZE_RESULTS_DIR, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)

                    # Extract relevante informatie
                    date_str = filename.split("_")[-1].replace(".json", "")
                    try:
                        date = datetime.datetime.strptime(date_str,
                                                          "%Y%m%d_%H%M%S").strftime(
                            "%Y-%m-%d")
                    except:
                        date = "Onbekend"

                    if "strategy" in data and "results" in data and len(
                        data["results"]) > 0:
                        best_result = data["results"][0]

                        results.append({
                            "date": date,
                            "type": "optimize",
                            "strategy": data.get("strategy", "unknown"),
                            "symbol": ", ".join(
                                data.get("symbols", ["unknown"])),
                            "timeframe": data.get("timeframe", "unknown"),
                            "return": best_result["metrics"].get(
                                "total_return_pct",
                                0) if "metrics" in best_result else 0,
                            "sharpe": best_result["metrics"].get("sharpe_ratio",
                                                                 0) if "metrics" in best_result else 0,
                            "filepath": filepath
                        })
                except Exception as e:
                    print(f"Fout bij laden van {filename}: {e}")

    return sorted(results, key=lambda x: x["date"], reverse=True)


def load_saved_profiles():
    """Laad opgeslagen backtest profielen met verbeterde foutafhandeling."""
    profiles = []

    try:
        if os.path.exists(PROFILE_DIR):
            for filename in os.listdir(PROFILE_DIR):
                if filename.endswith(".json"):
                    try:
                        filepath = os.path.join(PROFILE_DIR, filename)
                        with open(filepath, 'r') as f:
                            data = json.load(f)

                        # Veilige extractie van gegevens met diepere error handling
                        profile_name = filename.replace(".json", "")

                        # Compatibiliteit met verschillende profielformaten
                        if isinstance(data, dict):
                            strategy_type = data.get("strategy", {})
                            if isinstance(strategy_type, dict):
                                strategy_type = strategy_type.get("type",
                                                                  "unknown")
                            elif isinstance(strategy_type, str):
                                pass  # Strategy is al een string
                            else:
                                strategy_type = "unknown"

                            symbols = data.get("symbols", ["unknown"])
                            if isinstance(symbols, list):
                                symbols = ", ".join(symbols)
                            elif isinstance(symbols, str):
                                symbols = symbols
                            else:
                                symbols = "unknown"

                            timeframe = data.get("timeframe", "unknown")
                        else:
                            strategy_type = "unknown"
                            symbols = "unknown"
                            timeframe = "unknown"

                        profiles.append({
                            "name": profile_name,
                            "strategy": strategy_type,
                            "symbols": symbols,
                            "timeframe": timeframe,
                            "filepath": filepath
                        })
                    except Exception as e:
                        print(f"Fout bij laden van profiel {filename}: {e}")
        else:
            st.warning(f"Profielmap niet gevonden: {PROFILE_DIR}")
    except Exception as e:
        st.error(f"Algemene fout bij laden profielen: {e}")

    return profiles


def save_profile(name, parameters):
    """Sla parameters op als profiel."""
    filepath = os.path.join(PROFILE_DIR, f"{name}.json")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(parameters, f, indent=2)
    return filepath


def run_backtest_command(params, output_callback=None):
    """Voer een backtest uit met de gegeven parameters."""
    command = ["python", "-m", "src.analysis.backtest"]

    # Voeg parameters toe
    command.extend(["--strategy", params["strategy"]])
    command.extend(
        ["--symbols"] + params["symbols"].replace(" ", "").split(","))
    command.extend(["--timeframe", params["timeframe"]])
    command.extend(["--period", params["period"]])
    command.extend(["--initial-cash", str(params["initial_cash"])])

    # Strategie-specifieke parameters
    if params["strategy"] == "turtle":
        command.extend(["--entry-period", str(params["entry_period"])])
        command.extend(["--exit-period", str(params["exit_period"])])
        command.extend(["--atr-period", str(params["atr_period"])])
        if params.get("vol_filter", False):
            command.append("--use-vol-filter")
    else:  # ema
        command.extend(["--fast-ema", str(params["fast_ema"])])
        command.extend(["--slow-ema", str(params["slow_ema"])])
        command.extend(["--signal-ema", str(params["signal_ema"])])
        command.extend(["--rsi-period", str(params["rsi_period"])])

    if params.get("plot", False):
        command.append("--plot")

    # Start process
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Lees output
    output = []
    for line in process.stdout:
        line = line.strip()
        output.append(line)
        if output_callback:
            output_callback(line)

    process.wait()
    return process.returncode, output


def run_optimization_command(params, output_callback=None):
    """Voer een optimalisatie uit met de gegeven parameters."""
    command = ["python", "-m", "src.analysis.optimizer"]

    # Voeg parameters toe
    command.extend(["--strategy", params["strategy"]])
    command.extend(
        ["--symbols"] + params["symbols"].replace(" ", "").split(","))
    command.extend(["--timeframe", params["timeframe"]])
    command.extend(["--period", params["period"]])
    command.extend(["--metric", params["metric"]])
    command.extend(["--max-combinations", str(params["max_combinations"])])

    # Strategie-specifieke parameters
    if params["strategy"] == "turtle":
        command.extend(["--entry-period-range", params["entry_range"]])
        command.extend(["--exit-period-range", params["exit_range"]])
        command.extend(["--atr-period-range", params["atr_range"]])
    else:  # ema
        command.extend(["--fast-ema-range", params["fast_ema_range"]])
        command.extend(["--slow-ema-range", params["slow_ema_range"]])
        command.extend(["--signal-ema-range", params["signal_ema_range"]])

    # Start process
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Lees output
    output = []
    for line in process.stdout:
        line = line.strip()
        output.append(line)
        if output_callback:
            output_callback(line)

    process.wait()
    return process.returncode, output


def create_candlestick_chart(df, title="Price Chart", volume=True,
                             indicators=None):
    """Creëer een candlestick chart met Plotly."""
    if df is None or len(df) == 0:
        return go.Figure().update_layout(title="Geen data beschikbaar")

    # Maak subplots: een voor prijs, een voor volume (indien geactiveerd)
    fig = make_subplots(
        rows=2 if volume else 1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=("Price", "Volume") if volume else ("Price",),
        row_heights=[0.8, 0.2] if volume else [1]
    )

    # Voeg candlestick chart toe
    fig.add_trace(
        go.Candlestick(
            x=df['time'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price"
        ),
        row=1, col=1
    )

    # Voeg volume toe indien gewenst
    if volume and 'tick_volume' in df.columns:
        fig.add_trace(
            go.Bar(
                x=df['time'],
                y=df['tick_volume'],
                name="Volume",
                marker_color='rgba(0, 0, 255, 0.5)'
            ),
            row=2, col=1
        )

    # Voeg indicators toe indien opgegeven
    if indicators:
        if 'ema1' in indicators and indicators['ema1'] > 0:
            ema1 = df['close'].ewm(span=indicators['ema1']).mean()
            fig.add_trace(
                go.Scatter(
                    x=df['time'],
                    y=ema1,
                    mode='lines',
                    name=f"EMA {indicators['ema1']}",
                    line=dict(color='rgba(255, 165, 0, 0.8)')
                ),
                row=1, col=1
            )

        if 'ema2' in indicators and indicators['ema2'] > 0:
            ema2 = df['close'].ewm(span=indicators['ema2']).mean()
            fig.add_trace(
                go.Scatter(
                    x=df['time'],
                    y=ema2,
                    mode='lines',
                    name=f"EMA {indicators['ema2']}",
                    line=dict(color='rgba(0, 0, 255, 0.8)')
                ),
                row=1, col=1
            )

        if 'bb' in indicators and indicators['bb']:
            # Bereken Bollinger Bands (20, 2)
            ma20 = df['close'].rolling(window=20).mean()
            std20 = df['close'].rolling(window=20).std()
            upper_band = ma20 + 2 * std20
            lower_band = ma20 - 2 * std20

            fig.add_trace(
                go.Scatter(
                    x=df['time'],
                    y=upper_band,
                    mode='lines',
                    name='Upper BB',
                    line=dict(color='rgba(173, 216, 230, 0.8)')
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df['time'],
                    y=ma20,
                    mode='lines',
                    name='Middle BB',
                    line=dict(color='rgba(173, 216, 230, 0.8)')
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df['time'],
                    y=lower_band,
                    mode='lines',
                    name='Lower BB',
                    line=dict(color='rgba(173, 216, 230, 0.8)')
                ),
                row=1, col=1
            )

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price",
        height=600,
        xaxis_rangeslider_visible=False
    )

    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig


# App hoofdstructuur
def main():
    # Navigatie
    st.sidebar.title("Sophia Trading Framework")

    # Diagnostiek weergave indien nodig
    if not SOPHIA_IMPORTS_SUCCESS:
        st.sidebar.warning("⚠️ Niet alle modules zijn geladen")
        with st.sidebar.expander("Import details", expanded=False):
            st.error(
                f"Import fout: {import_error if 'import_error' in locals() else 'Onbekende fout'}")
            st.info("Het dashboard werkt in beperkte modus.")
    else:
        st.sidebar.success("✅ Alle modules geladen")

    # Tabs
    tab_options = ["Backtest", "Optimalisatie", "Live Trading", "Data & Charts"]
    selected_tab = st.sidebar.radio("Navigatie", tab_options)

    # Tab inhoud
    if selected_tab == "Backtest":
        show_backtest_tab()
    elif selected_tab == "Optimalisatie":
        show_optimize_tab()
    elif selected_tab == "Live Trading":
        show_live_trading_tab()
    elif selected_tab == "Data & Charts":
        show_data_charts_tab()


def show_backtest_tab():
    st.title("📊 Backtest")

    # Layout met twee kolommen
    col1, col2 = st.columns([1, 2])

    with col1:
        # Parameters sectie
        st.subheader("Backtest Parameters")

        # Basis parameters
        st.session_state.backtest_params["strategy"] = st.selectbox(
            "Strategie",
            ["turtle", "ema"],
            index=0 if st.session_state.backtest_params[
                           "strategy"] == "turtle" else 1,
            key="bt_strategy"
        )

        st.session_state.backtest_params["symbols"] = st.text_input(
            "Symbolen (komma-gescheiden)",
            value=st.session_state.backtest_params["symbols"],
            key="bt_symbols"
        )

        st.session_state.backtest_params["timeframe"] = st.selectbox(
            "Timeframe",
            ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
            index=["M1", "M5", "M15", "M30", "H1", "H4", "D1"].index(
                st.session_state.backtest_params["timeframe"]),
            key="bt_timeframe"
        )

        st.session_state.backtest_params["period"] = st.selectbox(
            "Periode",
            ["1m", "3m", "6m", "1y", "2y", "5y"],
            index=["1m", "3m", "6m", "1y", "2y", "5y"].index(
                st.session_state.backtest_params["period"]),
            key="bt_period"
        )

        st.session_state.backtest_params["initial_cash"] = st.number_input(
            "Initieel Kapitaal",
            min_value=1.0,
            value=float(st.session_state.backtest_params["initial_cash"]),
            key="bt_initial_cash"
        )

        st.session_state.backtest_params["plot"] = st.checkbox(
            "Genereer grafieken",
            value=st.session_state.backtest_params["plot"],
            key="bt_plot"
        )

        # Strategie-specifieke parameters
        st.subheader(
            f"{'Turtle' if st.session_state.backtest_params['strategy'] == 'turtle' else 'EMA'} Strategie Parameters")

        if st.session_state.backtest_params["strategy"] == "turtle":
            st.session_state.backtest_params["entry_period"] = st.number_input(
                "Entry Period",
                min_value=1,
                value=int(st.session_state.backtest_params["entry_period"]),
                key="bt_entry_period"
            )

            st.session_state.backtest_params["exit_period"] = st.number_input(
                "Exit Period",
                min_value=1,
                value=int(st.session_state.backtest_params["exit_period"]),
                key="bt_exit_period"
            )

            st.session_state.backtest_params["atr_period"] = st.number_input(
                "ATR Period",
                min_value=1,
                value=int(st.session_state.backtest_params["atr_period"]),
                key="bt_atr_period"
            )

            st.session_state.backtest_params["vol_filter"] = st.checkbox(
                "Gebruik volatiliteitsfilter",
                value=st.session_state.backtest_params["vol_filter"],
                key="bt_vol_filter"
            )
        else:  # EMA strategie
            st.session_state.backtest_params["fast_ema"] = st.number_input(
                "Fast EMA",
                min_value=1,
                value=int(st.session_state.backtest_params["fast_ema"]),
                key="bt_fast_ema"
            )

            st.session_state.backtest_params["slow_ema"] = st.number_input(
                "Slow EMA",
                min_value=1,
                value=int(st.session_state.backtest_params["slow_ema"]),
                key="bt_slow_ema"
            )

            st.session_state.backtest_params["signal_ema"] = st.number_input(
                "Signal EMA",
                min_value=1,
                value=int(st.session_state.backtest_params["signal_ema"]),
                key="bt_signal_ema"
            )

            st.session_state.backtest_params["rsi_period"] = st.number_input(
                "RSI Period",
                min_value=1,
                value=int(st.session_state.backtest_params["rsi_period"]),
                key="bt_rsi_period"
            )

        # Profiel opslaan sectie
        st.subheader("Profiel Opslaan")
        profile_name = st.text_input("Profielnaam", key="bt_profile_name")
        save_button = st.button("Profiel Opslaan")

        if save_button and profile_name:
            try:
                filepath = save_profile(profile_name,
                                        st.session_state.backtest_params)
                st.success(f"Profiel opgeslagen als: {profile_name}")
            except Exception as e:
                st.error(f"Fout bij opslaan profiel: {e}")

        # Run Backtest knop
        run_button = st.button(
            "Start Backtest",
            disabled=st.session_state.backtest_running,
            use_container_width=True,
            type="primary"
        )

        if run_button:
            st.session_state.backtest_running = True
            st.session_state.backtest_output = []

            # Start een aparte thread voor de backtest
            import threading

            def update_output(line):
                st.session_state.backtest_output.append(line)

            def run_backtest_thread():
                try:
                    _, output = run_backtest_command(
                        st.session_state.backtest_params, update_output)
                    st.session_state.backtest_running = False
                except Exception as e:
                    st.session_state.backtest_output.append(f"Error: {e}")
                    st.session_state.backtest_running = False

            thread = threading.Thread(target=run_backtest_thread)
            thread.start()

    with col2:
        # Backtest output en resultaten
        output_tab, profiles_tab, results_tab = st.tabs(
            ["Backtest Output", "Opgeslagen Profielen", "Backtest Resultaten"])

        with output_tab:
            # Console output
            st.subheader("Backtest Console Output")

            if st.session_state.backtest_running:
                st.info("Backtest loopt... even geduld")
                progress_bar = st.progress(0)

                # Toon de output
                output_container = st.container()
                with output_container:
                    for i, line in enumerate(st.session_state.backtest_output):
                        st.text(line)
                        # Update progress bar (eenvoudige simulatie)
                        if i % 3 == 0:
                            progress = min(i / 20, 1.0)
                            progress_bar.progress(progress)
            else:
                # Toon de output
                for line in st.session_state.backtest_output:
                    st.text(line)

                # Clear output knop
                if st.button("Wis Console Output", key="clear_bt_output"):
                    st.session_state.backtest_output = []
                    st.experimental_rerun()

        with profiles_tab:
            st.subheader("Opgeslagen Profielen")

            # Laad profielen
            profiles = load_saved_profiles()

            if not profiles:
                st.info("Geen opgeslagen profielen gevonden")
            else:
                # Maak een DataFrame voor weergave
                profile_df = pd.DataFrame(profiles)
                profile_df = profile_df[
                    ["name", "strategy", "symbols", "timeframe"]]

                # Toon tabel
                st.dataframe(profile_df, use_container_width=True)

                # Selecteer een profiel om te laden
                selected_profile = st.selectbox(
                    "Selecteer een profiel om te laden",
                    [p["name"] for p in profiles],
                    key="bt_selected_profile"
                )

                if st.button("Laad Profiel", key="load_profile_btn"):
                    # Zoek het geselecteerde profiel
                    for profile in profiles:
                        if profile["name"] == selected_profile:
                            # Laad profiel
                            try:
                                with open(profile["filepath"], 'r') as f:
                                    loaded_profile = json.load(f)

                                # Update session state
                                # Haal basis parameters op
                                st.session_state.backtest_params[
                                    "strategy"] = loaded_profile.get("strategy",
                                                                     {}).get(
                                    "type", "turtle")
                                st.session_state.backtest_params[
                                    "symbols"] = ",".join(
                                    loaded_profile.get("symbols", ["EURUSD"]))
                                st.session_state.backtest_params[
                                    "timeframe"] = loaded_profile.get(
                                    "timeframe", "H4")

                                # Strategie parameters
                                strategy_params = loaded_profile.get("strategy",
                                                                     {})
                                if st.session_state.backtest_params[
                                    "strategy"] == "turtle":
                                    st.session_state.backtest_params[
                                        "entry_period"] = strategy_params.get(
                                        "entry_period", 20)
                                    st.session_state.backtest_params[
                                        "exit_period"] = strategy_params.get(
                                        "exit_period", 10)
                                    st.session_state.backtest_params[
                                        "atr_period"] = strategy_params.get(
                                        "atr_period", 14)
                                    st.session_state.backtest_params[
                                        "vol_filter"] = strategy_params.get(
                                        "vol_filter", True)
                                else:  # ema
                                    st.session_state.backtest_params[
                                        "fast_ema"] = strategy_params.get(
                                        "fast_ema", 9)
                                    st.session_state.backtest_params[
                                        "slow_ema"] = strategy_params.get(
                                        "slow_ema", 21)
                                    st.session_state.backtest_params[
                                        "signal_ema"] = strategy_params.get(
                                        "signal_ema", 5)

                                st.success(
                                    f"Profiel '{selected_profile}' geladen")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Fout bij laden profiel: {e}")

        with results_tab:
            st.subheader("Backtest Resultaten")

            # Laad resultaten
            backtest_results = load_backtest_results()

            if not backtest_results:
                st.info("Geen backtest resultaten gevonden")
            else:
                # Maak een DataFrame voor weergave
                results_df = pd.DataFrame(backtest_results)
                results_df = results_df[
                    ["date", "strategy", "symbol", "timeframe", "return",
                     "sharpe"]]
                results_df["return"] = results_df["return"].apply(
                    lambda x: f"{x:.2f}%")
                results_df["sharpe"] = results_df["sharpe"].apply(
                    lambda x: f"{x:.2f}")
                results_df.columns = ["Datum", "Strategie", "Symbool",
                                      "Timeframe", "Return", "Sharpe"]

                # Toon tabel
                st.dataframe(results_df, use_container_width=True)

                # Selecteer een resultaat om details te bekijken
                selected_result_idx = st.selectbox(
                    "Selecteer een resultaat om details te bekijken",
                    range(len(backtest_results)),
                    format_func=lambda
                        i: f"{backtest_results[i]['date']} - {backtest_results[i]['strategy']} {backtest_results[i]['symbol']} {backtest_results[i]['timeframe']}",
                    key="bt_selected_result"
                )

                # Toon details
                st.subheader("Resultaat Details")
                result = backtest_results[selected_result_idx]

                # Maak een mooie weergave van het resultaat
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Return", f"{result['return']:.2f}%")
                with col2:
                    st.metric("Sharpe Ratio", f"{result['sharpe']:.2f}")
                with col3:
                    st.metric("Strategie", result['strategy'].upper())

                # Probeer om de bestandspaden van de resultaatafbeeldingen te vinden
                result_base = os.path.basename(result['filepath']).replace(
                    ".json", "")

                # Controleer of er een afbeelding is
                image_path = os.path.join(BACKTEST_RESULTS_DIR,
                                          f"{result_base}.png")
                if os.path.exists(image_path):
                    st.image(image_path,
                             caption=f"{result['strategy'].upper()} backtest resultaat",
                             use_column_width=True)
                else:
                    st.warning("Geen afbeelding gevonden voor dit resultaat")


def show_optimize_tab():
    st.title("⚙️ Optimalisatie")

    # Layout met twee kolommen
    col1, col2 = st.columns([1, 2])

    with col1:
        # Parameters sectie
        st.subheader("Optimalisatie Parameters")

        # Basis parameters
        st.session_state.optimize_params["strategy"] = st.selectbox(
            "Strategie",
            ["turtle", "ema"],
            index=0 if st.session_state.optimize_params[
                           "strategy"] == "turtle" else 1,
            key="opt_strategy"
        )

        st.session_state.optimize_params["symbols"] = st.text_input(
            "Symbool",
            value=st.session_state.optimize_params["symbols"],
            key="opt_symbols"
        )

        st.session_state.optimize_params["timeframe"] = st.selectbox(
            "Timeframe",
            ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
            index=["M1", "M5", "M15", "M30", "H1", "H4", "D1"].index(
                st.session_state.optimize_params["timeframe"]),
            key="opt_timeframe"
        )

        st.session_state.optimize_params["period"] = st.selectbox(
            "Periode",
            ["1m", "3m", "6m", "1y", "2y", "5y"],
            index=["1m", "3m", "6m", "1y", "2y", "5y"].index(
                st.session_state.optimize_params["period"]),
            key="opt_period"
        )

        st.session_state.optimize_params["metric"] = st.selectbox(
            "Optimalisatie Metric",
            ["sharpe", "return", "drawdown", "profit_factor"],
            index=["sharpe", "return", "drawdown", "profit_factor"].index(
                st.session_state.optimize_params["metric"]),
            key="opt_metric"
        )

        st.session_state.optimize_params["max_combinations"] = st.number_input(
            "Maximum Combinaties",
            min_value=1,
            value=int(st.session_state.optimize_params["max_combinations"]),
            key="opt_max_combinations"
        )

        # Strategie-specifieke parameters
        st.subheader(
            f"{'Turtle' if st.session_state.optimize_params['strategy'] == 'turtle' else 'EMA'} Parameter Ranges")

        if st.session_state.optimize_params["strategy"] == "turtle":
            st.session_state.optimize_params["entry_range"] = st.text_input(
                "Entry Period Range (komma-gescheiden)",
                value=st.session_state.optimize_params["entry_range"],
                key="opt_entry_range"
            )

            st.session_state.optimize_params["exit_range"] = st.text_input(
                "Exit Period Range (komma-gescheiden)",
                value=st.session_state.optimize_params["exit_range"],
                key="opt_exit_range"
            )

            st.session_state.optimize_params["atr_range"] = st.text_input(
                "ATR Period Range (komma-gescheiden)",
                value=st.session_state.optimize_params["atr_range"],
                key="opt_atr_range"
            )
        else:  # EMA strategie
            st.session_state.optimize_params["fast_ema_range"] = st.text_input(
                "Fast EMA Range (komma-gescheiden)",
                value=st.session_state.optimize_params["fast_ema_range"],
                key="opt_fast_ema_range"
            )

            st.session_state.optimize_params["slow_ema_range"] = st.text_input(
                "Slow EMA Range (komma-gescheiden)",
                value=st.session_state.optimize_params["slow_ema_range"],
                key="opt_slow_ema_range"
            )

            st.session_state.optimize_params[
                "signal_ema_range"] = st.text_input(
                "Signal EMA Range (komma-gescheiden)",
                value=st.session_state.optimize_params["signal_ema_range"],
                key="opt_signal_ema_range"
            )

        # Run Optimize knop
        run_button = st.button(
            "Start Optimalisatie",
            disabled=st.session_state.optimize_running,
            use_container_width=True,
            type="primary"
        )

        if run_button:
            st.session_state.optimize_running = True
            st.session_state.optimize_output = []

            # Start een aparte thread voor de optimalisatie
            import threading

            def update_output(line):
                st.session_state.optimize_output.append(line)

            def run_optimize_thread():
                try:
                    _, output = run_optimization_command(
                        st.session_state.optimize_params, update_output)
                    st.session_state.optimize_running = False
                except Exception as e:
                    st.session_state.optimize_output.append(f"Error: {e}")
                    st.session_state.optimize_running = False

            thread = threading.Thread(target=run_optimize_thread)
            thread.start()

    with col2:
        # Optimalisatie output en resultaten
        output_tab, best_tab, history_tab = st.tabs(
            ["Optimalisatie Output", "Beste Parameters",
             "Optimalisatie Geschiedenis"])

        with output_tab:
            # Console output
            st.subheader("Optimalisatie Console Output")

            if st.session_state.optimize_running:
                st.info("Optimalisatie loopt... even geduld")
                progress_bar = st.progress(0)

                # Toon de output
                output_container = st.container()
                with output_container:
                    for i, line in enumerate(st.session_state.optimize_output):
                        st.text(line)
                        # Update progress bar (eenvoudige simulatie)
                        if i % 3 == 0:
                            progress = min(i / 20, 1.0)
                            progress_bar.progress(progress)
            else:
                # Toon de output
                for line in st.session_state.optimize_output:
                    st.text(line)

                # Clear output knop
                if st.button("Wis Console Output", key="clear_opt_output"):
                    st.session_state.optimize_output = []
                    st.experimental_rerun()

        with best_tab:
            st.subheader("Beste Parameters")

            # Controleer of er optimalisatie resultaten zijn
            best_params = None

            # Zoek naar "BEST PARAMETERS FOUND:" in output
            found_best = False
            params_dict = {}
            for line in st.session_state.optimize_output:
                if found_best and line.strip():
                    # Parse parameters regels van het format "  key: value"
                    if line.strip().startswith("  "):
                        parts = line.strip()[2:].split(":", 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            # Convert waarden naar juiste types
                            if value.lower() == "true":
                                value = True
                            elif value.lower() == "false":
                                value = False
                            elif value.replace(".", "", 1).isdigit():
                                value = float(value) if "." in value else int(
                                    value)
                            params_dict[key] = value

                if "BEST PARAMETERS FOUND:" in line:
                    found_best = True

            if params_dict:
                best_params = params_dict

                # Toon de beste parameters
                st.success("Optimale parameters gevonden!")

                # Maak een mooie weergave
                col1, col2 = st.columns(2)
                for i, (key, value) in enumerate(best_params.items()):
                    with col1 if i % 2 == 0 else col2:
                        st.metric(key, value)

                # Knop om parameters toe te passen op backtest
                if st.button("Parameters toepassen op backtest",
                             key="apply_best_params"):
                    # Strategy type vaststellen
                    strategy_type = st.session_state.optimize_params["strategy"]

                    # Update backtest parameters
                    st.session_state.backtest_params["strategy"] = strategy_type

                    # Turtle parameters
                    if strategy_type == "turtle":
                        if "entry_period" in best_params:
                            st.session_state.backtest_params["entry_period"] = \
                            best_params["entry_period"]
                        if "exit_period" in best_params:
                            st.session_state.backtest_params["exit_period"] = \
                            best_params["exit_period"]
                        if "atr_period" in best_params:
                            st.session_state.backtest_params["atr_period"] = \
                            best_params["atr_period"]
                        if "use_vol_filter" in best_params:
                            st.session_state.backtest_params["vol_filter"] = \
                            best_params["use_vol_filter"]

                    # EMA parameters
                    else:
                        if "fast_ema" in best_params:
                            st.session_state.backtest_params["fast_ema"] = \
                            best_params["fast_ema"]
                        if "slow_ema" in best_params:
                            st.session_state.backtest_params["slow_ema"] = \
                            best_params["slow_ema"]
                        if "signal_ema" in best_params:
                            st.session_state.backtest_params["signal_ema"] = \
                            best_params["signal_ema"]

                    st.success(
                        "Parameters toegepast! Ga naar de Backtest tab om een test uit te voeren.")
            else:
                st.info(
                    "Run een optimalisatie om de beste parameters te vinden")

        with history_tab:
            st.subheader("Optimalisatie Geschiedenis")

            # Laad optimalisatie resultaten
            optimize_results = load_optimization_results()

            if not optimize_results:
                st.info("Geen optimalisatie resultaten gevonden")
            else:
                # Maak een DataFrame voor weergave
                results_df = pd.DataFrame(optimize_results)
                results_df = results_df[
                    ["date", "strategy", "symbol", "timeframe", "return",
                     "sharpe"]]
                results_df["return"] = results_df["return"].apply(
                    lambda x: f"{x:.2f}%")
                results_df["sharpe"] = results_df["sharpe"].apply(
                    lambda x: f"{x:.2f}")
                results_df.columns = ["Datum", "Strategie", "Symbool",
                                      "Timeframe", "Return", "Sharpe"]

                # Toon tabel
                st.dataframe(results_df, use_container_width=True)

                # Selecteer een resultaat om details te bekijken
                if len(optimize_results) > 0:
                    selected_result_idx = st.selectbox(
                        "Selecteer een resultaat om details te bekijken",
                        range(len(optimize_results)),
                        format_func=lambda
                            i: f"{optimize_results[i]['date']} - {optimize_results[i]['strategy']} {optimize_results[i]['symbol']} {optimize_results[i]['timeframe']}",
                        key="opt_selected_result"
                    )

                    # Toon details
                    result = optimize_results[selected_result_idx]

                    # Probeer om de bestandspaden van de resultaatafbeeldingen te vinden
                    result_base = os.path.basename(result['filepath']).replace(
                        ".json", "")

                    # Controleer of er een afbeelding is
                    image_path = os.path.join(OPTIMIZE_RESULTS_DIR,
                                              f"{result_base}.png")
                    if os.path.exists(image_path):
                        st.image(image_path,
                                 caption=f"{result['strategy'].upper()} optimalisatie resultaat",
                                 use_column_width=True)
                    else:
                        st.warning(
                            "Geen afbeelding gevonden voor dit resultaat")


def show_live_trading_tab():
    st.title("🚀 Live Trading")

    # Layout met twee kolommen
    col1, col2 = st.columns([1, 2])

    with col1:
        # MT5 Verbinding sectie
        st.subheader("MT5 Verbinding")

        # Status container
        status_container = st.container()
        with status_container:
            if st.session_state.live_params["connected"]:
                st.success("Verbonden met MetaTrader 5")
            else:
                st.warning("Niet verbonden met MetaTrader 5")

        # Connect/Disconnect knop
        if st.session_state.live_params["connected"]:
            if st.button("Verbreek Verbinding", type="secondary",
                         use_container_width=True):
                # Simuleer verbreken verbinding
                st.session_state.live_params["connected"] = False
                st.session_state.live_output.append("Verbinding verbroken")

                # Clear positions
                st.session_state.positions = []

                st.experimental_rerun()
        else:
            if st.button("Verbind met MT5", type="secondary",
                         use_container_width=True):
                # Simuleer verbinding maken
                if SOPHIA_IMPORTS_SUCCESS:
                    try:
                        config = load_config()
                        connector = MT5Connector(config.get("mt5", {}))
                        if connector.connect():
                            st.session_state.live_params["connected"] = True
                            st.session_state.live_output.append(
                                "Verbonden met MetaTrader 5")

                            # Get account info
                            account_info = connector.get_account_info()
                            st.session_state.live_output.append(
                                f"Account balans: {account_info.get('balance', 'onbekend')}")

                            connector.disconnect()
                            st.experimental_rerun()
                        else:
                            st.error(
                                "Kon geen verbinding maken met MetaTrader 5")
                            st.session_state.live_output.append(
                                "Kon geen verbinding maken met MetaTrader 5")
                    except Exception as e:
                        st.error(f"Fout bij verbinden: {e}")
                        st.session_state.live_output.append(
                            f"Fout bij verbinden: {e}")
                else:
                    # Demo mode
                    st.session_state.live_params["connected"] = True
                    st.session_state.live_output.append(
                        "Verbonden met MetaTrader 5 (demo mode)")
                    st.experimental_rerun()

        # Trading Parameters sectie
        st.subheader("Trading Parameters")

        # Basis parameters
        strategy = st.selectbox(
            "Strategie",
            ["turtle", "ema"],
            index=0 if st.session_state.live_params[
                           "strategy"] == "turtle" else 1,
            key="live_strategy",
            disabled=st.session_state.live_params.get("trading", False)
        )
        st.session_state.live_params["strategy"] = strategy

        symbols = st.text_input(
            "Symbolen (komma-gescheiden)",
            value=st.session_state.live_params["symbols"],
            key="live_symbols",
            disabled=st.session_state.live_params.get("trading", False)
        )
        st.session_state.live_params["symbols"] = symbols

        timeframe = st.selectbox(
            "Timeframe",
            ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
            index=["M1", "M5", "M15", "M30", "H1", "H4", "D1"].index(
                st.session_state.live_params["timeframe"]),
            key="live_timeframe",
            disabled=st.session_state.live_params.get("trading", False)
        )
        st.session_state.live_params["timeframe"] = timeframe

        risk = st.number_input(
            "Risico %",
            min_value=0.1,
            max_value=10.0,
            value=float(st.session_state.live_params["risk"]),
            key="live_risk",
            disabled=st.session_state.live_params.get("trading", False)
        )
        st.session_state.live_params["risk"] = risk

        interval = st.number_input(
            "Check Interval (sec)",
            min_value=1,
            value=int(st.session_state.live_params["interval"]),
            key="live_interval",
            disabled=st.session_state.live_params.get("trading", False)
        )
        st.session_state.live_params["interval"] = interval

        # Trading Buttons
        st.subheader("Trading Controls")

        buttons_col1, buttons_col2 = st.columns(2)

        with buttons_col1:
            if st.session_state.live_params.get("trading", False):
                if st.button("Stop Trading", type="primary",
                             use_container_width=True):
                    st.session_state.live_params["trading"] = False
                    st.session_state.live_output.append(
                        "=== Live Trading Gestopt ===")
                    st.experimental_rerun()
            else:
                if st.button("Start Trading", type="primary",
                             use_container_width=True,
                             disabled=not st.session_state.live_params[
                                 "connected"]):
                    st.session_state.live_params["trading"] = True
                    st.session_state.live_output.append(
                        "=== Live Trading Gestart ===")
                    st.session_state.live_output.append(
                        f"Strategie: {st.session_state.live_params['strategy']}")
                    st.session_state.live_output.append(
                        f"Symbolen: {st.session_state.live_params['symbols']}")
                    st.session_state.live_output.append(
                        f"Timeframe: {st.session_state.live_params['timeframe']}")
                    st.session_state.live_output.append(
                        f"Risico per trade: {st.session_state.live_params['risk']}%")
                    st.session_state.live_output.append(
                        f"Check interval: {st.session_state.live_params['interval']} seconden")

                    # Demo positie toevoegen
                    symbol = st.session_state.live_params["symbols"].split(",")[
                        0]
                    st.session_state.positions.append({
                        "symbol": symbol,
                        "direction": "BUY",
                        "size": 0.1,
                        "entry": 1.2345,
                        "current": 1.2360,
                        "profit": "+15.00 €"
                    })

                    st.session_state.live_output.append(
                        f"Order geplaatst: BUY 0.1 {symbol} @ 1.2345")

                    st.experimental_rerun()

        with buttons_col2:
            if st.button("Sluit Alle Posities", type="secondary",
                         use_container_width=True,
                         disabled=not st.session_state.live_params[
                             "connected"] or len(
                             st.session_state.positions) == 0):
                if len(st.session_state.positions) > 0:
                    st.session_state.live_output.append(
                        "Alle posities worden gesloten...")
                    for pos in st.session_state.positions:
                        st.session_state.live_output.append(
                            f"Sluit positie: {pos['direction']} {pos['size']} {pos['symbol']} @ {pos['current']}")
                    st.session_state.positions = []
                    st.session_state.live_output.append(
                        "Alle posities zijn gesloten")
                    st.experimental_rerun()

    with col2:
        # Account Overzicht
        st.subheader("Account Overzicht")

        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

        # Simuleer account metrics
        with metrics_col1:
            if st.session_state.live_params["connected"]:
                st.metric("Account Balans", "10,000.00 €")
            else:
                st.metric("Account Balans", "-")

        with metrics_col2:
            if st.session_state.live_params["connected"]:
                equity = 10000.0
                profit_sum = sum(
                    [float(pos["profit"].replace("€", "").strip()) for pos in
                     st.session_state.positions]) if st.session_state.positions else 0.0
                equity += profit_sum
                st.metric("Equity", f"{equity:.2f} €")
            else:
                st.metric("Equity", "-")

        with metrics_col3:
            if st.session_state.live_params["connected"]:
                st.metric("Margin", "0.00 €")
            else:
                st.metric("Margin", "-")

        with metrics_col4:
            if st.session_state.live_params["connected"]:
                profit_sum = sum(
                    [float(pos["profit"].replace("€", "").strip()) for pos in
                     st.session_state.positions]) if st.session_state.positions else 0.0
                st.metric("Open P/L", f"{profit_sum:.2f} €",
                          delta=f"{profit_sum:.2f} €")
            else:
                st.metric("Open P/L", "-")

        # Open Posities
        st.subheader("Open Posities")

        if not st.session_state.positions:
            st.info("Geen open posities")
        else:
            # Maak een DataFrame
            positions_df = pd.DataFrame(st.session_state.positions)

            # Format de DataFrame
            positions_df.columns = ["Symbool", "Richting", "Grootte", "Entry",
                                    "Huidig", "Winst/Verlies"]

            # Toon de DataFrame
            st.dataframe(positions_df, use_container_width=True)

        # Trading Log
        st.subheader("Trading Log")

        # Toon de output
        log_container = st.container(height=300)
        with log_container:
            for line in st.session_state.live_output:
                if "===" in line:
                    st.markdown(f"**{line}**")
                elif "ERROR" in line or "Fout" in line:
                    st.error(line)
                elif "Verbonden" in line or "succesvol" in line:
                    st.success(line)
                else:
                    st.text(line)

        # Clear log knop
        if st.button("Wis Log", key="clear_live_log"):
            st.session_state.live_output = []
            st.experimental_rerun()


def show_data_charts_tab():
    st.title("📈 Data & Charts")

    # Layout met twee kolommen
    col1, col2 = st.columns([1, 2])

    with col1:
        # Data Instellingen sectie
        st.subheader("Data Instellingen")

        symbol = st.text_input(
            "Symbool",
            value=st.session_state.data_params["symbol"],
            key="data_symbol"
        )
        st.session_state.data_params["symbol"] = symbol

        timeframe = st.selectbox(
            "Timeframe",
            ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
            index=["M1", "M5", "M15", "M30", "H1", "H4", "D1"].index(
                st.session_state.data_params["timeframe"]),
            key="data_timeframe"
        )
        st.session_state.data_params["timeframe"] = timeframe

        from_date = st.date_input(
            "Van Datum",
            value=pd.to_datetime(st.session_state.data_params["from_date"]),
            key="data_from_date"
        )
        st.session_state.data_params["from_date"] = from_date.strftime(
            "%Y-%m-%d")

        to_date = st.date_input(
            "Tot Datum",
            value=pd.to_datetime(st.session_state.data_params["to_date"]),
            key="data_to_date"
        )
        st.session_state.data_params["to_date"] = to_date.strftime("%Y-%m-%d")

        # Chart Opties
        st.subheader("Chart Opties")

        chart_type = st.selectbox(
            "Chart Type",
            ["candle", "line", "ohlc"],
            index=["candle", "line", "ohlc"].index(
                st.session_state.data_params["chart_type"]),
            key="data_chart_type"
        )
        st.session_state.data_params["chart_type"] = chart_type

        show_ema = st.checkbox(
            "Toon EMA lijnen",
            value=st.session_state.data_params["show_ema"],
            key="data_show_ema"
        )
        st.session_state.data_params["show_ema"] = show_ema

        if show_ema:
            ema1_col, ema2_col = st.columns(2)

            with ema1_col:
                ema1 = st.number_input(
                    "EMA 1 Periode",
                    min_value=1,
                    value=int(st.session_state.data_params["ema1"]),
                    key="data_ema1"
                )
                st.session_state.data_params["ema1"] = ema1

            with ema2_col:
                ema2 = st.number_input(
                    "EMA 2 Periode",
                    min_value=1,
                    value=int(st.session_state.data_params["ema2"]),
                    key="data_ema2"
                )
                st.session_state.data_params["ema2"] = ema2

        show_bb = st.checkbox(
            "Toon Bollinger Bands",
            value=st.session_state.data_params["show_bb"],
            key="data_show_bb"
        )
        st.session_state.data_params["show_bb"] = show_bb

        show_volume = st.checkbox(
            "Toon Volume",
            value=st.session_state.data_params["show_volume"],
            key="data_show_volume"
        )
        st.session_state.data_params["show_volume"] = show_volume

        # Update Chart knop
        if st.button("Update Chart", type="primary", use_container_width=True):
            # Haal data op
            df = fetch_mt5_data(
                st.session_state.data_params["symbol"],
                st.session_state.data_params["timeframe"],
                st.session_state.data_params["from_date"],
                st.session_state.data_params["to_date"]
            )

            # Sla data op in session state
            st.session_state.chart_data = df

            # Geef feedback
            if df is not None and len(df) > 0:
                st.success(
                    f"Data opgehaald: {len(df)} bars voor {st.session_state.data_params['symbol']} {st.session_state.data_params['timeframe']}")
            else:
                st.error("Geen data gevonden voor deze parameters")

    with col2:
        # Chart sectie
        st.subheader(
            f"{st.session_state.data_params['symbol']} {st.session_state.data_params['timeframe']} Chart")

        # Toon chart indien data beschikbaar is
        if st.session_state.chart_data is not None and len(
            st.session_state.chart_data) > 0:
            # Indicator parameters
            indicators = None
            if st.session_state.data_params["show_ema"] or \
                st.session_state.data_params["show_bb"]:
                indicators = {}
                if st.session_state.data_params["show_ema"]:
                    indicators["ema1"] = st.session_state.data_params["ema1"]
                    indicators["ema2"] = st.session_state.data_params["ema2"]
                if st.session_state.data_params["show_bb"]:
                    indicators["bb"] = True

            # Maak chart
            fig = create_candlestick_chart(
                st.session_state.chart_data,
                title=f"{st.session_state.data_params['symbol']} {st.session_state.data_params['timeframe']}",
                volume=st.session_state.data_params["show_volume"],
                indicators=indicators
            )

            # Toon chart
            st.plotly_chart(fig, use_container_width=True)

            # Data Explorer
            st.subheader("Data Verkenner")

            # Toon een tabel met de data
            data_df = st.session_state.chart_data.copy()

            # Format de data
            data_df["time"] = pd.to_datetime(data_df["time"])
            data_df = data_df.sort_values("time", ascending=False)

            # Toon alleen de belangrijkste kolommen
            data_display = data_df[["time", "open", "high", "low", "close",
                                    "tick_volume" if "tick_volume" in data_df.columns else "volume"]]

            # Hernoem kolommen
            data_display.columns = ["Tijd", "Open", "Hoog", "Laag", "Sluit",
                                    "Volume"]

            # Toon de DataFrame
            st.dataframe(data_display, use_container_width=True)
        else:
            # Placeholder voor de chart
            st.info(
                "Geen data beschikbaar. Gebruik 'Update Chart' om data te laden.")


if __name__ == "__main__":
    main()