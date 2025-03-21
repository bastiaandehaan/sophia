# src/utils.py
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """
    Configureer logging voor de Sophia Trading applicatie.

    Args:
        log_level: Logging level, standaard INFO

    Returns:
        Logger object voor de applicatie
    """
    # Zorg dat src map bestaat
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"sophia_{datetime.now().strftime('%Y%m%d')}.log")

    # Configureer de root logger
    logging.basicConfig(level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()], )

    # Maak een specifieke logger voor Sophia
    logger = logging.getLogger("sophia")
    logger.setLevel(log_level)

    return logger


def load_config(config_path: str = "config/settings.json") -> Dict[str, Any]:
    """
    Laad configuratie uit JSON bestand.

    Args:
        config_path: Pad naar het configuratiebestand

    Returns:
        Dictionary met configuratie-instellingen
    """
    try:
        with open(config_path, "r") as file:
            config = json.load(file)

        # Valideer essentiële configuratie-elementen
        if "mt5" not in config:
            logging.error("Ontbrekende MT5 configuratie in settings.json")
            return {}

        if "symbols" not in config or not config["symbols"]:
            logging.warning(
                "Geen handelssymbolen gedefinieerd, standaard EURUSD wordt gebruikt")
            config["symbols"] = ["EURUSD"]

        return config

    except FileNotFoundError:
        logging.error(f"Configuratiebestand niet gevonden: {config_path}")
        return {}

    except json.JSONDecodeError:
        logging.error(f"Ongeldige JSON in configuratiebestand: {config_path}")
        return {}

    except Exception as e:
        logging.error(f"Fout bij laden configuratie: {e}")
        return {}


def save_config(config: Dict[str, Any],
        config_path: str = "config/settings.json") -> bool:
    """
    Slaat configuratie op naar JSON bestand.

    Args:
        config: Dictionary met configuratie-instellingen
        config_path: Pad waar de configuratie wordt opgeslagen

    Returns:
        bool: True als opslaan succesvol was, anders False
    """
    try:
        # Zorg dat directory bestaat
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        with open(config_path, "w") as file:
            json.dump(config, file, indent=2)

        return True

    except Exception as e:
        logging.error(f"Fout bij opslaan configuratie: {e}")
        return False


def format_price(price: float, symbol: str = "EURUSD") -> str:
    """
    Formatteer een prijs met de juiste precisie voor het symbool.

    Args:
        price: Prijs om te formatteren
        symbol: Handelssymbool

    Returns:
        str: Geformatteerde prijs
    """
    # JPY paren hebben normaal 3 decimalen, andere forex 5 decimalen
    decimals = 3 if symbol.endswith("JPY") else 5
    return f"{price:.{decimals}f}"


def calculate_pip_value(symbol: str, lot_size: float = 1.0,
        account_currency: str = "USD") -> float:
    """
    Bereken de waarde van 1 pip voor het gegeven symbool.

    Args:
        symbol: Handelssymbool
        lot_size: Grootte van de positie in lots
        account_currency: Valuta van het account

    Returns:
        float: Waarde van 1 pip in account valuta
    """
    # Vereenvoudigde pip waarde berekening
    # In werkelijkheid zou je de koers van de tweede valuta naar account valuta moeten gebruiken

    # Standaard pip waarden voor 1 standaard lot (100,000 eenheden)
    if symbol.endswith("JPY"):
        pip_value = 1000  # 0.01 pip waarde voor 1 standaard lot
    else:
        pip_value = 10  # 0.0001 pip waarde voor 1 standaard lot

    # Schaal op basis van lot grootte
    return pip_value * lot_size


def get_symbol_precision(symbol: str) -> int:
    """
    Krijg de prijsprecisie (aantal decimalen) voor een symbool.

    Args:
        symbol: Handelssymbool

    Returns:
        int: Aantal decimalen voor het symbool
    """
    # Vereenvoudigde precisie regels
    if symbol.endswith("JPY"):
        return 3  # JPY paren hebben typisch 3 decimalen
    return 5  # Andere forex paren hebben typisch 5 decimalen
