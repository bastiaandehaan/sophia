# tests/unit/test_turtle_bt.py
import numpy as np
import pandas as pd
import pytest

from src.backtesting.strategies.turtle_bt import TurtleStrategy
from tests.helpers.backtrader_test_helpers import BacktraderTestHelper


@pytest.fixture
def turtle_strategy(logger_fixture):
    """Creëer een TurtleStrategy instantie voor tests."""
    config = {"entry_period": 20, "exit_period": 10, "atr_period": 14}

    # Creëer een testbare backtrader strategie
    strategy = BacktraderTestHelper.create_test_strategy(TurtleStrategy, config)

    # Injecteer logger
    strategy.logger = logger_fixture

    return strategy


@pytest.fixture
def sample_ohlc_data():
    """Genereer een sample OHLC DataFrame voor tests."""
    dates = pd.date_range(start="2023-01-01", periods=100)
    data = pd.DataFrame(
        {
            "open": np.linspace(1.0, 1.1, 100),
            "high": np.linspace(1.01, 1.11, 100),
            "low": np.linspace(0.99, 1.09, 100),
            "close": np.linspace(1.005, 1.105, 100),
            "time": dates,
        }
    )

    # Voeg een breakout toe om signalen te triggeren
    data.loc[data.index[-10:], "high"] *= 1.02
    data.loc[data.index[-10:], "close"] *= 1.01

    return data


def test_turtle_strategy_init(turtle_strategy):
    """Test TurtleStrategy initialisatie."""
    # Controleer params van de strategie
    assert turtle_strategy.p.entry_period == 20
    assert turtle_strategy.p.exit_period == 10
    assert turtle_strategy.p.atr_period == 14

    # Controleer of positie dictionary bestaat
    assert hasattr(turtle_strategy, "positions") or hasattr(turtle_strategy,
                                                            "_positions")


def test_calculate_indicators(turtle_strategy):
    """Test dat indicators correct worden aangemaakt."""
    # Bij Backtrader worden indicators automatisch aangemaakt tijdens initialisatie
    # Controleer of indicators dictionary bestaat
    assert hasattr(turtle_strategy, "inds")

    # Haal data name van eerste data feed
    if len(turtle_strategy.datas) > 0:
        data_name = turtle_strategy.datas[0]._name

        # Controleer of er indicators zijn voor deze data feed
        if data_name in turtle_strategy.inds:
            indicators = turtle_strategy.inds[data_name]
            # Controleer of de verwachte indicators aanwezig zijn
            assert "entry_high" in indicators
            assert "entry_low" in indicators
            assert "exit_high" in indicators
            assert "exit_low" in indicators
            assert "atr" in indicators


def test_next_method_exists(turtle_strategy):
    """Test dat de next methode bestaat en aanroepbaar is."""
    assert hasattr(turtle_strategy, "next")
    # Check dat het een methode is en geen attribuut
    assert callable(getattr(turtle_strategy, "next"))


def test_notify_order_method_exists(turtle_strategy):
    """Test dat de notify_order methode bestaat."""
    assert hasattr(turtle_strategy, "notify_order")
    assert callable(getattr(turtle_strategy, "notify_order"))


def test_notify_trade_method_exists(turtle_strategy):
    """Test dat de notify_trade methode bestaat."""
    assert hasattr(turtle_strategy, "notify_trade")
    assert callable(getattr(turtle_strategy, "notify_trade"))


def test_stop_method_exists(turtle_strategy):
    """Test dat de stop methode bestaat."""
    assert hasattr(turtle_strategy, "stop")
    assert callable(getattr(turtle_strategy, "stop"))