# src/utils.py
import json
import logging
from datetime import datetime
import os


def setup_logging():
    """Configureer eenvoudige logging"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"sophia_{datetime.now().strftime('%Y%m%d')}.log")

    logging.basicConfig(level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()])

    return logging.getLogger("sophia")


def load_config(config_path="config/settings.json"):
    """Laad configuratie uit JSON bestand"""
    try:
        with open(config_path, "r") as file:
            return json.load(file)
    except Exception as e:
        logger = logging.getLogger("sophia")
        logger.error(f"Fout bij laden configuratie: {e}")
        return {}