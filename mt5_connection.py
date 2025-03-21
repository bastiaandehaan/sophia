#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MT5 Connection Tester for Sophia Trading Framework
Tests MT5 connectivity and basic functionality
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Configure logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sophia.mt5_test")

try:
    import MetaTrader5 as mt5
except ImportError:
    logger.error(
        "MetaTrader5 package not installed. Install with: pip install MetaTrader5"
    )
    sys.exit(1)

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "settings.json")


def print_separator():
    """Print a separator line."""
    print("=" * 80)


def load_config(config_path=CONFIG_PATH):
    """Load configuration from settings.json."""
    logger.info(f"Loading configuration from {config_path}")
    try:
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found at: {config_path}")
            return None

        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return None


def find_mt5_installation():
    """Find MT5 installation path."""
    common_paths = [
        r"C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe",
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
    ]

    for path in common_paths:
        if os.path.exists(path):
            logger.info(f"Found MT5 installation at: {path}")
            return path

    return None


def test_mt5_connection():
    """Test MT5 connection and basic functionality."""
    print_separator()
    logger.info("Starting MT5 Connection Test")
    print_separator()

    # Load configuration
    config = load_config()
    if not config:
        return False

    mt5_config = config.get("mt5", {})
    if not mt5_config:
        logger.error("No MT5 configuration found in settings.json")
        return False

    login = mt5_config.get("login", 0)
    password = mt5_config.get("password", "")
    server = mt5_config.get("server", "")
    mt5_path = mt5_config.get("mt5_path", "")

    logger.info(f"MT5 Config: Server={server}, Login={login}, Path={mt5_path}")

    # Verify MT5 path
    if not os.path.exists(mt5_path):
        logger.warning(f"MT5 path not found: {mt5_path}")
        alt_path = find_mt5_installation()
        if alt_path:
            mt5_path = alt_path
            logger.info(f"Using alternative MT5 path: {mt5_path}")

            # Update config with correct path
            mt5_config["mt5_path"] = mt5_path
            config["mt5"] = mt5_config
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Updated configuration with correct MT5 path")
        else:
            logger.error("No valid MT5 installation found")
            return False

    # Initialize MT5
    logger.info(f"Initializing MT5 with path: {mt5_path}")
    mt5.shutdown()  # Make sure MT5 is shut down first

    if not mt5.initialize(path=mt5_path):
        error = mt5.last_error()
        logger.error(f"Failed to initialize MT5: {error}")
        return False

    logger.info("MT5 initialized successfully")

    # Login to MT5
    logger.info(f"Logging in to MT5 server: {server}")
    if not mt5.login(login=login, password=password, server=server):
        error = mt5.last_error()
        logger.error(f"Failed to login to MT5: {error}")
        mt5.shutdown()
        return False

    logger.info(f"Successfully logged in to MT5")

    # Get account info
    logger.info("Getting account information...")
    account_info = mt5.account_info()
    if account_info:
        logger.info("Account information retrieved:")
        logger.info(f"  Name: {account_info.name}")
        logger.info(f"  Server: {account_info.server}")
        logger.info(f"  Balance: {account_info.balance} {account_info.currency}")
        logger.info(f"  Equity: {account_info.equity} {account_info.currency}")
        logger.info(f"  Leverage: 1:{account_info.leverage}")
    else:
        error = mt5.last_error()
        logger.error(f"Failed to get account info: {error}")

    # Get available symbols
    logger.info("Getting available symbols...")
    symbols = mt5.symbols_get()
    if symbols:
        logger.info(f"Retrieved {len(symbols)} symbols")
        logger.info("First 5 symbols:")
        for i, symbol in enumerate(symbols[:5]):
            logger.info(f"  - {symbol.name}")
    else:
        error = mt5.last_error()
        logger.error(f"Failed to get symbols: {error}")

    # Get historical data for EURUSD
    logger.info("Getting historical data for EURUSD...")
    rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H4, 0, 10)
    if rates is not None and len(rates) > 0:
        logger.info(f"Retrieved {len(rates)} bars for EURUSD")
        for i, rate in enumerate(rates[:3]):
            time_str = datetime.fromtimestamp(rate[0]).strftime("%Y-%m-%d %H:%M")
            logger.info(
                f"  Bar {i}: Time={time_str}, Open={rate[1]}, High={rate[2]}, Low={rate[3]}, Close={rate[4]}"
            )
    else:
        error = mt5.last_error()
        logger.error(f"Failed to get historical data: {error}")

    # Shutdown MT5
    logger.info("Shutting down MT5...")
    mt5.shutdown()
    logger.info("MT5 connection test completed")

    return True


if __name__ == "__main__":
    test_mt5_connection()
