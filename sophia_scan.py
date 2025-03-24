#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for the Sophia Trading Framework Dashboard.

Test de geïsoleerde functionaliteit van dashboard.py, inclusief Streamlit-specifieke logica,
met mocking voor externe afhankelijkheden.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

# Zorg dat project root in sys.path staat
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Importeer de te testen module
try:
    from src.backtesting.dashboard import (
        generate_demo_data,
        create_candlestick_chart,
        load_config,
        save_config,
        fetch_mt5_data,
        run_backtest,
    )
except ImportError as e:
    pytest.skip(f"Kan dashboard niet importeren: {e}", allow_module_level=True)

# Mock Streamlit om UI-aanroepen te simuleren
@pytest.fixture
def mock_streamlit():
    with patch("streamlit.session_state", new=dict()) as mock_session:
        with patch("streamlit.warning") as mock_warning:
            with patch("streamlit.success") as mock_success:
                with patch("streamlit.error") as mock_error:
                    yield {
                        "session_state": mock_session,
                        "warning": mock_warning,
                        "success": mock_success,
                        "error": mock_error,
                    }

# Mock MT5Connector voor data-ophaaltests
@pytest.fixture
def mock_mt5_connector():
    with patch("src.backtesting.dashboard.MT5Connector") as mock_connector:
        mock_instance = MagicMock()
        mock_connector.return_value = mock_instance
        mock_instance.connect.return_value = True
        mock_instance.get_historical_data.return_value = pd.DataFrame({
            "time": pd.date_range("2023-01-01", periods=10, freq="H"),
            "open": np.linspace(1.1, 1.2, 10),
            "high": np.linspace(1.15, 1.25, 10),
            "low": np.linspace(1.05, 1.15, 10),
            "close": np.linspace(1.1, 1.2, 10),
            "tick_volume": np.random.randint(100, 1000, 10),
        })
        mock_instance.disconnect.return_value = None
        yield mock_instance

# Sample data fixture
@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "time": pd.date_range("2023-01-01", periods=10, freq="H"),
        "open": np.linspace(1.1, 1.2, 10),
        "high": np.linspace(1.15, 1.25, 10),
        "low": np.linspace(1.05, 1.15, 10),
        "close": np.linspace(1.1, 1.2, 10),
        "tick_volume": np.random.randint(100, 1000, 10),
    })

# --- Unit Tests ---

def test_generate_demo_data_basic():
    """Test basisfunctionaliteit van demo-datageneratie."""
    symbol = "EURUSD"
    from_date = "2023-01-01"
    to_date = "2023-01-31"
    df = generate_demo_data(symbol, from_date, to_date)

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert set(df.columns) == {"time", "open", "high", "low", "close", "tick_volume"}
    assert pd.api.types.is_datetime64_any_dtype(df["time"])
    assert all(df["high"] >= df["low"])
    assert all(df["open"] <= df["high"])
    assert all(df["open"] >= df["low"])

def test_generate_demo_data_invalid_dates():
    """Test demo-datageneratie met ongeldige datums."""
    symbol = "EURUSD"
    from_date = "2023-02-01"  # Later dan to_date
    to_date = "2023-01-01"
    df = generate_demo_data(symbol, from_date, to_date)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0  # Verwacht lege DataFrame bij ongeldige volgorde

def test_create_candlestick_chart_basic(sample_data):
    """Test basisfunctionaliteit van candlestick chart."""
    fig = create_candlestick_chart(sample_data, "Test Chart")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # Candlestick + Volume
    assert fig.data[0].type == "candlestick"
    assert fig.data[1].type == "bar"
    assert fig.layout.title.text == "Test Chart"

def test_create_candlestick_chart_no_volume(sample_data):
    """Test chart zonder volume."""
    fig = create_candlestick_chart(sample_data, "No Volume", volume=False)
    assert len(fig.data) == 1  # Alleen candlestick
    assert fig.data[0].type == "candlestick"
    assert fig.layout.xaxis.rangeslider.visible is False

def test_create_candlestick_chart_with_indicators(sample_data):
    """Test chart met EMA-indicatoren."""
    indicators = {"show_ema": True, "ema1": 5, "ema2": 10}
    fig = create_candlestick_chart(sample_data, "With Indicators", indicators=indicators)
    assert len(fig.data) == 4  # Candlestick + Volume + 2 EMA's
    assert fig.data[1].type == "scatter"  # EMA 5
    assert fig.data[2].type == "scatter"  # EMA 10
    assert "EMA 5" in [trace.name for trace in fig.data]

def test_create_candlestick_chart_empty_data():
    """Test chart met lege data."""
    df = pd.DataFrame()
    fig = create_candlestick_chart(df, "Empty Chart")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0
    assert "Geen data beschikbaar" in fig.layout.title.text

def test_load_config_file_exists():
    """Test laden van configuratiebestand dat bestaat."""
    mock_data = {"mt5": {"server": "test"}}
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        with patch("pathlib.Path.exists", return_value=True):
            config = load_config("dummy/path.json")
    assert config == mock_data

def test_load_config_file_missing():
    """Test laden van niet-bestaand configuratiebestand."""
    with patch("pathlib.Path.exists", return_value=False):
        config = load_config("dummy/path.json")
    assert config == {}

def test_save_config_success():
    """Test succesvol opslaan van configuratie."""
    config = {"test": "value"}
    with patch("builtins.open", mock_open()) as mock_file:
        with patch("pathlib.Path.parent.mkdir") as mock_mkdir:
            result = save_config(config, "dummy/path.json")
    assert result is True
    mock_file().write.assert_called_once()
    mock_mkdir.assert_called_once_with(exist_ok=True, parents=True)

def test_fetch_mt5_data_success(mock_streamlit, mock_mt5_connector):
    """Test succesvol ophalen van MT5-data."""
    with patch("src.backtesting.dashboard.load_config", return_value={"mt5": {"server": "test"}}):
        with patch("src.backtesting.dashboard.SOPHIA_IMPORTS_SUCCESS", True):
            df = fetch_mt5_data("EURUSD", "H4", "2023-01-01", "2023-01-31")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 10
    mock_mt5_connector.connect.assert_called_once()

def test_fetch_mt5_data_no_config(mock_streamlit):
    """Test MT5-data ophalen zonder configuratie."""
    with patch("src.backtesting.dashboard.load_config", return_value={}):
        with patch("src.backtesting.dashboard.SOPHIA_IMPORTS_SUCCESS", True):
            df = fetch_mt5_data("EURUSD", "H4", "2023-01-01", "2023-01-31")
    assert len(df) > 0  # Valt terug op demo-data
    mock_streamlit["warning"].assert_called_once()

# --- Integratietests ---

def test_run_backtest_basic(mock_streamlit):
    """Test basisuitvoering van backtest."""
    params = {
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
    }
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = ["Loading data", "Backtest complete"]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        returncode, output = run_backtest(params)
    assert returncode == 0
    assert len(output) == 2
    mock_popen.assert_called_once()

def test_run_backtest_failure(mock_streamlit):
    """Test mislukte backtest."""
    params = {"strategy": "turtle", "symbols": "EURUSD", "timeframe": "H4", "period": "1y"}
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = ["Error occurred"]
        mock_process.wait.return_value = 1
        mock_popen.return_value = mock_process
        returncode, output = run_backtest(params)
    assert returncode == 1
    assert "Error" in output[0]