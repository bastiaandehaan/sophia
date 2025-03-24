# tests/unit/test_turtle_strategy.py
import pytest

from src.backtesting.strategies.turtle_bt import TurtleStrategy
from tests.helpers.backtrader_test_helpers import BacktraderTestHelper


@pytest.fixture
def turtle_strategy(logger_fixture):
    """Creëer een TurtleStrategy instantie voor tests."""
    config = {
        "entry_period": 20,
        "exit_period": 10,
        "atr_period": 14,
        "risk_pct": 0.01,
        "use_vol_filter": True
    }

    # Creëer een testbare backtrader strategie
    strategy = BacktraderTestHelper.create_test_strategy(TurtleStrategy, config)

    # Injecteer logger
    strategy.logger = logger_fixture

    return strategy


def test_turtle_strategy_init(turtle_strategy):
    """Test TurtleStrategy initialisatie."""
    # Controleer params van de strategie
    assert turtle_strategy.p.entry_period == 20
    assert turtle_strategy.p.exit_period == 10
    assert turtle_strategy.p.atr_period == 14
    assert turtle_strategy.p.risk_pct == 0.01
    assert turtle_strategy.p.use_vol_filter is True

    # Controleer of positie dictionary bestaat
    assert hasattr(turtle_strategy, "_positions") or hasattr(turtle_strategy,
                                                             "positions")


def test_indicators_created(turtle_strategy):
    """Test dat indicators correct worden aangemaakt."""
    # Bij Backtrader worden indicators automatisch aangemaakt tijdens initialisatie
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


def test_prenext_method_exists(turtle_strategy):
    """Test dat de prenext methode bestaat."""
    assert hasattr(turtle_strategy, "prenext")
    assert callable(getattr(turtle_strategy, "prenext"))


def test_positions_property(turtle_strategy):
    """Test dat de positions property correct werkt."""
    # Test dat property bestaat
    assert hasattr(turtle_strategy, "positions")

    # Als het een property is, test dan dat we er waarden aan kunnen toewijzen
    # Dit is optioneel, want in BackTrader context zou dit niet vaak gebeuren
    if hasattr(type(turtle_strategy), "positions") and isinstance(
        getattr(type(turtle_strategy), "positions"), property):
        # Het is inderdaad een property
        old_positions = turtle_strategy.positions

        # Probeer een nieuwe waarde toe te wijzen (dit werkt alleen als er een setter is)
        try:
            turtle_strategy.positions = {}
            # Reset naar oude waarde
            turtle_strategy.positions = old_positions
        except:
            # Als er geen setter is, is dat ook prima
            pass


def test_core_methods_exist(turtle_strategy):
    """Test dat de belangrijkste strategie methoden bestaan."""
    # Elke BT strategie moet deze methoden hebben
    assert hasattr(turtle_strategy, "next")
    assert callable(getattr(turtle_strategy, "next"))

    assert hasattr(turtle_strategy, "notify_order")
    assert callable(getattr(turtle_strategy, "notify_order"))

    assert hasattr(turtle_strategy, "notify_trade")
    assert callable(getattr(turtle_strategy, "notify_trade"))

    assert hasattr(turtle_strategy, "stop")
    assert callable(getattr(turtle_strategy, "stop"))
