# tests/unit/test_ema_bt.py
import pytest

from src.backtesting.strategies.ema_bt import EMAStrategy
from tests.helpers.backtrader_test_helpers import BacktraderTestHelper


@pytest.fixture
def ema_strategy(logger_fixture):
    """Creëer een EMAStrategy instantie voor tests."""
    config = {
        "fast_ema": 9,
        "slow_ema": 21,
        "signal_ema": 5,
        "rsi_period": 14,
    }

    # Creëer een testbare backtrader strategie
    strategy = BacktraderTestHelper.create_test_strategy(EMAStrategy, config)

    # Injecteer logger
    strategy.logger = logger_fixture

    return strategy


def test_ema_strategy_init(ema_strategy):
    """Test EMAStrategy initialisatie."""
    # Controleer params van de strategie
    assert ema_strategy.p.fast_ema == 9
    assert ema_strategy.p.slow_ema == 21
    assert ema_strategy.p.signal_ema == 5
    assert ema_strategy.p.rsi_period == 14

    # Controleer of positie dictionary bestaat
    assert hasattr(ema_strategy, "positions")


def test_indicators_created(ema_strategy):
    """Test dat indicators correct worden aangemaakt."""
    # Bij Backtrader worden indicators automatisch aangemaakt tijdens initialisatie
    assert hasattr(ema_strategy, "inds")

    # Haal data name van eerste data feed
    if len(ema_strategy.datas) > 0:
        data_name = ema_strategy.datas[0]._name

        # Controleer of er indicators zijn voor deze data feed
        if data_name in ema_strategy.inds:
            indicators = ema_strategy.inds[data_name]
            # Controleer of de verwachte indicators aanwezig zijn
            assert "fast_ema" in indicators
            assert "slow_ema" in indicators
            assert "macd" in indicators
            assert "signal" in indicators
            assert "macd_hist" in indicators
            assert "rsi" in indicators
            assert "atr" in indicators


def test_helper_methods_exist(ema_strategy):
    """Test dat de helper methoden bestaan."""
    assert hasattr(ema_strategy, "_set_stop_loss")
    assert callable(getattr(ema_strategy, "_set_stop_loss"))

    assert hasattr(ema_strategy, "_set_profit_target")
    assert callable(getattr(ema_strategy, "_set_profit_target"))

    assert hasattr(ema_strategy, "_update_trailing_stop")
    assert callable(getattr(ema_strategy, "_update_trailing_stop"))

    assert hasattr(ema_strategy, "_is_in_session")
    assert callable(getattr(ema_strategy, "_is_in_session"))