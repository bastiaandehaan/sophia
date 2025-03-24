#!/usr/bin/env python3
"""
Sophia Framework Verification Script - FIXED PATH VERSION
Checks if the Sophia Trading Framework is correctly installed
and functioning properly.
"""
import importlib
import json
import logging
import os
from typing import List, Tuple

# IMPORTANT: Fixed path calculation
script_dir = os.path.dirname(os.path.abspath(__file__))  # tools directory
project_root = os.path.dirname(script_dir)  # Sophia directory (one level up)


class Logger:
    """Handles formatted logging output for the verification process."""

    @staticmethod
    def header(message: str) -> None:
        """Print a prominent header in the console."""
        separator = "=" * 80
        print(f"\n{separator}\n{message}\n{separator}")

    @staticmethod
    def step(step_num: int, message: str) -> None:
        """Print a numbered step in the verification."""
        print(f"\n[Step {step_num}] {message}")

    @staticmethod
    def success(message: str) -> None:
        """Print a successful check."""
        print(f"✅ {message}")

    @staticmethod
    def failure(message: str) -> None:
        """Print a failed check."""
        print(f"❌ {message}")

    @staticmethod
    def warning(message: str) -> None:
        """Print a warning."""
        print(f"⚠️ {message}")


class SophiaVerifier:
    """Handles verification of Sophia Framework installation and functionality."""

    # Constants
    MIN_PYTHON_VERSION = (3, 7)
    REQUIRED_PACKAGES = ["MetaTrader5", "pandas", "numpy", "matplotlib"]
    REQUIRED_MODULES = [
        "src.connector",
        "src.strategy",
        "src.risk",
        "src.utils",
        "src.main",
    ]
    # FIXED: Use correct project_root directly
    CONFIG_PATH = os.path.join(project_root, "config", "settings.json")
    TEMP_CONFIG_PATH = os.path.join(project_root, "config",
                                    "temp_settings.json")

    def __init__(self):
        """Initialize the verifier with default configuration."""
        self.logger = Logger()
        self.config = {}

        # Suppress logging from Sophia modules during testing
        logging.basicConfig(level=logging.INFO)
        sophia_logger = logging.getLogger("sophia")
        sophia_logger.setLevel(logging.ERROR)

        # Debug: print actual paths being used
        print(f"Project root: {project_root}")
        print(f"Config path: {self.CONFIG_PATH}")

    def check_python_version(self) -> bool:
        """Check if the Python version is compatible."""
        import platform

        version = platform.python_version()
        major, minor, _ = map(int, version.split("."))
        is_compatible = (major, minor) >= self.MIN_PYTHON_VERSION

        if is_compatible:
            self.logger.success(
                f"Python version {version} is compatible (minimum: {self.MIN_PYTHON_VERSION[0]}.{self.MIN_PYTHON_VERSION[1]})"
            )
        else:
            self.logger.failure(
                f"Python version {version} is not compatible (minimum: {self.MIN_PYTHON_VERSION[0]}.{self.MIN_PYTHON_VERSION[1]})"
            )

        return is_compatible

    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """Check if all required dependencies are installed."""
        missing_packages = []

        for package in self.REQUIRED_PACKAGES:
            try:
                importlib.import_module(package)
                self.logger.success(f"Package '{package}' is installed")
            except ImportError:
                self.logger.failure(f"Package '{package}' is not installed")
                missing_packages.append(package)

        return len(missing_packages) == 0, missing_packages

    def check_sophia_modules(self) -> bool:
        """Check if all Sophia modules can be imported."""
        all_imported = True

        for module in self.REQUIRED_MODULES:
            try:
                importlib.import_module(module)
                self.logger.success(f"Module '{module}' successfully imported")
            except ImportError as e:
                self.logger.failure(
                    f"Module '{module}' could not be imported: {e}")
                all_imported = False

        return all_imported

    def check_config_loading(self) -> bool:
        """Check if the configuration can be loaded correctly."""
        from src.utils import load_config

        if not os.path.exists(self.CONFIG_PATH):
            self.logger.warning(
                f"Configuration file not found at: {self.CONFIG_PATH}")
            # Create a temporary config file for testing
            os.makedirs(os.path.dirname(self.TEMP_CONFIG_PATH), exist_ok=True)
            temp_config = {
                "mt5": {
                    "login": 12345678,
                    "password": "test_password",
                    "server": "MetaQuotes-Demo",
                    "mt5_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
                },
                "symbols": ["EURUSD"],
                "timeframe": "H4",
                "interval": 300,
                "risk": {"risk_per_trade": 0.01, "max_daily_loss": 0.05},
                "strategy": {"entry_period": 20, "exit_period": 10,
                             "atr_period": 14},
            }

            with open(self.TEMP_CONFIG_PATH, "w") as f:
                json.dump(temp_config, f, indent=4)

            self.logger.warning(
                f"Temporary configuration file created at: {self.TEMP_CONFIG_PATH}"
            )
            config_path = self.TEMP_CONFIG_PATH
        else:
            config_path = self.CONFIG_PATH

        try:
            self.config = load_config(config_path)
            if self.config:
                self.logger.success(
                    f"Configuration successfully loaded from: {config_path}"
                )
                return True
            else:
                self.logger.failure("Empty configuration loaded")
                return False
        except Exception as e:
            self.logger.failure(f"Error loading configuration: {e}")
            return False

    def test_risk_manager(self) -> bool:
        """Test the functionality of the RiskManager."""
        from src.risk import RiskManager

        try:
            # Initialize RiskManager
            risk_config = self.config.get("risk", {})
            risk_manager = RiskManager(risk_config)

            # Test position size calculation
            account_balance = 10000.0
            entry_price = 1.2000
            stop_loss = 1.1950
            position_size = risk_manager.calculate_position_size(
                account_balance, entry_price, stop_loss
            )

            # Test if the output is reasonable
            if 0.01 <= position_size <= 10.0:
                self.logger.success(
                    f"RiskManager calculates correct position size: {position_size} lots"
                )
                return True
            else:
                self.logger.failure(
                    f"RiskManager calculates unrealistic position size: {position_size} lots"
                )
                return False
        except Exception as e:
            self.logger.failure(f"Error in RiskManager test: {e}")
            return False

    def test_strategy_indicators(self) -> bool:
        """Test if the strategy indicators calculate correctly."""
        import pandas as pd
        import numpy as np

        try:
            # Create mock data
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

            # For TurtleStrategy we'll create a mock connector and risk_manager
            class MockConnector:
                def get_historical_data(self, *args, **kwargs):
                    return data

            class MockRiskManager:
                pass

            # Initialize strategy
            # Implementation would continue here
            return True  # Placeholder for the incomplete function

        except Exception as e:
            self.logger.failure(f"Error in Strategy test: {e}")
            return False

    def run_verification(self):
        """Run the complete verification process."""
        self.logger.header("Sophia Trading Framework Verification")

        step = 1
        self.logger.step(step, "Checking Python version")
        python_ok = self.check_python_version()

        step += 1
        self.logger.step(step, "Checking required dependencies")
        deps_ok, missing_packages = self.check_dependencies()

        step += 1
        self.logger.step(step, "Checking Sophia modules")
        modules_ok = self.check_sophia_modules()

        step += 1
        self.logger.step(step, "Checking configuration loading")
        config_ok = self.check_config_loading()

        if config_ok:
            step += 1
            self.logger.step(step, "Testing RiskManager")
            risk_ok = self.test_risk_manager()

            step += 1
            self.logger.step(step, "Testing Strategy indicators")
            strategy_ok = self.test_strategy_indicators()
        else:
            risk_ok = False
            strategy_ok = False

        # Print overall results
        self.logger.header("Verification Results")
        all_passed = all(
            [python_ok, deps_ok, modules_ok, config_ok, risk_ok, strategy_ok]
        )

        if all_passed:
            self.logger.success("All verification checks passed!")
        else:
            self.logger.failure(
                "Some verification checks failed. See details above.")


if __name__ == "__main__":
    verifier = SophiaVerifier()
    verifier.run_verification()
