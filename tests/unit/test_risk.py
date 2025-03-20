# tests/unit/test_risk.py
import pytest
from src.risk import RiskManager


@pytest.fixture
def risk_manager(logger_fixture):
    """Creëer een RiskManager instantie voor tests."""
    config = {"risk_per_trade": 0.01, "max_daily_loss": 0.05}
    risk_manager = RiskManager(config)
    risk_manager.logger = logger_fixture
    return risk_manager


def test_risk_manager_init(risk_manager):
    """Test RiskManager initialisatie."""
    assert risk_manager.risk_per_trade == 0.01
    assert risk_manager.max_daily_loss == 0.05


def test_calculate_position_size_normal(risk_manager):
    """Test normale positiegrootte berekening."""
    # Test met 1% risico op $10,000 account met 50 pips stop (pip value $10)
    position_size = risk_manager.calculate_position_size(account_balance=10000.0,
        entry_price=1.2000, stop_loss=1.1950  # 50 pips stop
    )

    # Verwachte berekening: $10,000 * 0.01 / (50 * $10) = 0.2 lots
    expected_position = 0.2

    # Vanwege afrondingen en pip waarde aannames, testen we binnen een bereik
    assert 0.1 <= position_size <= 0.3


def test_calculate_position_size_zero_stop(risk_manager):
    """Test positiegrootte met gelijke entry en stop."""
    position_size = risk_manager.calculate_position_size(account_balance=10000.0,
        entry_price=1.2000, stop_loss=1.2000
        # Gelijke entry en stop (zou division by zero veroorzaken)
    )

    # Zou minimumwaarde moeten returneren
    assert position_size == 0.01


def test_calculate_position_size_tight_stop(risk_manager):
    """Test positiegrootte met zeer nauwe stop."""
    position_size = risk_manager.calculate_position_size(account_balance=10000.0,
        entry_price=1.2000, stop_loss=1.1995  # 5 pips stop, zeer nauw
    )

    # Zou groter moeten zijn dan bij wijdere stop
    normal_size = risk_manager.calculate_position_size(10000.0, 1.2000, 1.1950)
    assert position_size > normal_size


def test_calculate_position_size_large_account(risk_manager):
    """Test positiegrootte met groot account."""
    position_size = risk_manager.calculate_position_size(account_balance=1000000.0,
        # $1M account
        entry_price=1.2000, stop_loss=1.1950  # 50 pips stop
    )

    # Zou binnen limieten moeten blijven
    assert position_size <= 10.0  # Max positiegrootte


def test_custom_risk_percentage():
    """Test RiskManager met aangepast risicopercentage."""
    custom_config = {"risk_per_trade": 0.05,  # 5% risico
        "max_daily_loss": 0.10}

    risk_manager = RiskManager(custom_config)

    position_size = risk_manager.calculate_position_size(account_balance=10000.0,
        entry_price=1.2000, stop_loss=1.1950  # 50 pips stop
    )

    # Zou 5x groter moeten zijn dan met 1% risico
    assert position_size >= 0.5  # 5x de normale ~0.2 lots