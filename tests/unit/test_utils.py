import json
import logging

from src.core.utils import load_config


def test_load_config_success(tmp_path, caplog):
    """Test dat load_config een geldig JSON-bestand met mt5-config correct laadt."""
    config_path = tmp_path / "config.json"
    config = {"mt5": {"path": "dummy"}, "symbols": ["EURUSD"], "test": "value"}
    with open(config_path, "w") as f:
        json.dump(config, f)

    with caplog.at_level(logging.WARNING):
        result = load_config(str(config_path))

    assert result == config
    assert "Geen handelssymbolen" not in caplog.text


def test_load_config_adds_default_symbols(tmp_path, caplog):
    """Test dat load_config standaard EURUSD toevoegt als symbols ontbreekt."""
    config_path = tmp_path / "config.json"
    config = {"mt5": {"path": "dummy"}}
    expected = {"mt5": {"path": "dummy"}, "symbols": ["EURUSD"]}
    with open(config_path, "w") as f:
        json.dump(config, f)

    with caplog.at_level(logging.WARNING):
        result = load_config(str(config_path))

    assert result == expected
    assert "Geen handelssymbolen" in caplog.text


def test_load_config_missing_mt5(tmp_path, caplog):
    """Test dat load_config een lege dict retourneert als mt5 ontbreekt."""
    config_path = tmp_path / "config.json"
    config = {"test": "value"}
    with open(config_path, "w") as f:
        json.dump(config, f)

    with caplog.at_level(logging.ERROR):
        result = load_config(str(config_path))

    assert result == {}
    assert "Ontbrekende MT5 configuratie" in caplog.text


def test_load_config_file_not_found(caplog):
    """Test dat load_config een lege dict retourneert bij een niet-bestaand bestand."""
    with caplog.at_level(logging.ERROR):
        result = load_config("non_existent_config.json")

    assert result == {}
    assert "Configuratiebestand niet gevonden" in caplog.text


def test_load_config_invalid_json(tmp_path, caplog):
    """Test dat load_config een lege dict retourneert bij ongeldige JSON."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        f.write("{invalid json")

    with caplog.at_level(logging.ERROR):
        result = load_config(str(config_path))

    assert result == {}
    assert "Ongeldige JSON" in caplog.text