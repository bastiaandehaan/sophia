#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/main.py
import argparse
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

"""
Main module voor het Sophia Trading Framework.

Beschrijving van functionaliteit volgt hier.
"""

# Voeg project root toe aan Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.utils import setup_logging, load_config, save_config
from src.core.connector import MT5Connector
from src.core.risk import RiskManager
from src.strategies.turtle_strategy import TurtleStrategy


class SophiaTrader:
    """
    Hoofdklasse voor de Sophia trading applicatie.
    Beheert de levenscyclus van de trading applicatie en coördineert componenten.
    """

    def __init__(self, config_path: Optional[str] = None,
                 backtest_mode: bool = False) -> None:
        """
        Initialiseer de Sophia Trader applicatie.

        Args:
            config_path: Optioneel pad naar configuratiebestand
            backtest_mode: Of de applicatie in backtest modus draait
        """
        # Setup logging
        self.logger = setup_logging()
        self.logger.info("====== Sophia Trading System ======")
        self.logger.info(
            f"Opgestart op {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Backtest mode flag
        self.backtest_mode = backtest_mode

        # Configuratie laden
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = os.path.join(project_root, "config",
                                            "settings.json")

        self.config = self._load_configuration()

        # Componenten
        self.connector = None
        self.risk_manager = None
        self.strategy = None

        # State tracking
        self.running = False
        self.last_run_time = time.time()

    def _load_configuration(self) -> Dict[str, Any]:
        """
        Laad configuratie en maak de standaardconfiguratie indien nodig.

        Returns:
            Dict met configuratie-instellingen
        """
        # Zorg dat config directory bestaat
        config_dir = os.path.dirname(self.config_path)
        os.makedirs(config_dir, exist_ok=True)

        # Maak standaardconfiguratie als deze niet bestaat
        if not os.path.exists(self.config_path):
            self.logger.warning(
                f"Configuratiebestand niet gevonden, standaardconfiguratie wordt gemaakt"
            )

            default_config = {
                "mt5": {
                    "server": "FTMO-Demo2",
                    "login": 1520533067,
                    "password": "UP7d??y4Wg",
                    "mt5_path": "C:\\Program Files\\FTMO Global Markets MT5 Terminal\\terminal64.exe",
                },
                "symbols": ["EURUSD", "USDJPY"],
                "timeframe": "H4",
                "interval": 300,
                "risk": {"risk_per_trade": 0.01, "max_daily_loss": 0.05},
                "strategy": {
                    "type": "turtle",
                    "entry_period": 20,
                    "exit_period": 10,
                    "atr_period": 14,
                    "vol_filter": True,
                    "vol_lookback": 100,
                    "vol_threshold": 1.2,
                },
            }

            # Sla standaardconfiguratie op
            if save_config(default_config, self.config_path):
                self.logger.info(
                    f"Standaardconfiguratie aangemaakt op {self.config_path}"
                )
                return default_config
            else:
                self.logger.error("Kon standaardconfiguratie niet opslaan")
                return {}

        # Laad bestaande configuratie
        config = load_config(self.config_path)
        if not config:
            self.logger.error("Kon configuratie niet laden, stoppen...")
            return {}

        return config

    def initialize_components(self) -> bool:
        """
        Initialiseer alle componenten met foutafhandeling.

        Returns:
            bool: True als initialisatie succesvol was
        """
        try:
            # Maak componenten aan
            self.connector = MT5Connector(self.config.get("mt5", {}))

            # Verbinding maken met MT5 (alleen in live modus)
            if not self.backtest_mode:
                connect_attempts = 0
                max_attempts = 3

                while connect_attempts < max_attempts:
                    if self.connector.connect():
                        break

                    connect_attempts += 1
                    self.logger.warning(
                        f"Poging {connect_attempts}/{max_attempts} om verbinding te maken met MT5 mislukt. Opnieuw proberen..."
                    )
                    time.sleep(5)

                if connect_attempts >= max_attempts:
                    self.logger.error(
                        "Kon geen verbinding maken met MT5 na meerdere pogingen, stoppen..."
                    )
                    return False

            # Haal account informatie op (alleen in live modus)
            if self.backtest_mode:
                account_info = {"balance": 10000, "currency": "USD"}
            else:
                try:
                    account_info = self.connector.get_account_info()
                    if not account_info or "balance" not in account_info:
                        self.logger.warning(
                            "Kon account informatie niet ophalen, gebruik standaard waarden"
                        )
                        account_info = {"balance": 10000, "currency": "USD"}
                except Exception as e:
                    self.logger.error(
                        f"Fout bij ophalen account informatie: {e}")
                    account_info = {"balance": 10000, "currency": "USD"}

            self.logger.info(
                f"Account balans: {account_info['balance']} {account_info.get('currency', '')}"
            )

            # Initialiseer risicomanager
            self.risk_manager = RiskManager(self.config.get("risk", {}))

            # Initialiseer strategie op basis van configuratie
            strategy_config = self.config.get("strategy", {})
            strategy_type = strategy_config.get("type", "turtle")

            if strategy_type == "turtle":
                self.strategy = TurtleStrategy(
                    self.connector, self.risk_manager, strategy_config
                )
            elif strategy_type == "ema":
                # Importeer EMA strategie alleen indien nodig
                from src.strategies.ema_strategy import EMAStrategy

                self.strategy = EMAStrategy(
                    self.connector, self.risk_manager, strategy_config
                )
            else:
                self.logger.error(
                    f"Onbekend strategie type: {strategy_type}, gebruik turtle"
                )
                self.strategy = TurtleStrategy(
                    self.connector, self.risk_manager, strategy_config
                )

            # Zorg ervoor dat positions dictionary bestaat
            if (
                not hasattr(self.strategy, "positions")
                or self.strategy.positions is None
            ):
                self.strategy.positions = {}

            return True

        except Exception as e:
            self.logger.error(f"Fout bij initialisatie componenten: {e}")
            self.logger.debug(traceback.format_exc())
            return False

    def run(self) -> None:
        """
        Start de hoofdtrading loop.
        """
        if not self.initialize_components():
            return 1

        # Set up signal handler voor graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

        # Start trading loop
        try:
            symbols = self.config.get("symbols", ["EURUSD", "USDJPY"])
            self.logger.info(f"Start trading voor symbolen: {symbols}")

            self.running = True

            while self.running:
                start_time = time.time()

                try:
                    # Verwerk alle symbolen
                    for symbol in symbols:
                        self._process_symbol(symbol)

                    # Wacht voor volgende iteratie, gecorrigeerd voor verwerkingstijd
                    interval = self.config.get("interval", 300)  # Seconden
                    elapsed = time.time() - start_time
                    wait_time = max(
                        0.1, interval - elapsed
                    )  # Minimaal 0.1 seconden wachten

                    self.logger.info(
                        f"Wacht {wait_time:.1f} seconden tot volgende check..."
                    )
                    time.sleep(wait_time)

                except Exception as e:
                    self.logger.error(f"Onverwachte fout in hoofdloop: {e}")
                    self.logger.debug(traceback.format_exc())
                    # Kleine pauze om CPU-verbruik te beperken bij herhaalde fouten
                    time.sleep(5)

        except KeyboardInterrupt:
            self.logger.info("Programma gestopt door gebruiker")
        except Exception as e:
            self.logger.critical(f"Kritieke fout in programma: {e}")
            self.logger.debug(traceback.format_exc())
        finally:
            self._cleanup()

        return 0

    def _process_symbol(self, symbol: str) -> None:
        """
        Verwerk een specifiek handelssymbool.

        Args:
            symbol: Handelssymbool om te verwerken
        """
        try:
            # Check voor signalen
            result = self.strategy.check_signals(symbol)

            if result and result.get("signal"):
                signal = result["signal"]
                meta = result.get("meta", {})

                # Voer signaal uit
                execution_result = self.strategy.execute_signal(result)

                if execution_result and execution_result.get("success"):
                    self.logger.info(
                        f"Signaal succesvol uitgevoerd: {symbol} {signal}")
                else:
                    self.logger.warning(
                        f"Signaal uitvoering mislukt: {symbol} {signal} - Reden: {execution_result.get('reason', 'onbekend')}"
                    )

        except Exception as e:
            self.logger.error(f"Fout bij verwerken signalen voor {symbol}: {e}")
            self.logger.debug(traceback.format_exc())

    def _signal_handler(self, sig, frame) -> None:
        """
        Handler voor SIGINT/SIGTERM signalen voor netjes afsluiten.
        """
        self.logger.info("Afsluitsignaal ontvangen, bezig met stoppen...")
        self.running = False

    def _cleanup(self) -> None:
        """
        Sluit resources netjes af.
        """
        try:
            if self.connector and not self.backtest_mode:
                disconnect_success = self.connector.disconnect()
                if disconnect_success:
                    self.logger.info("Verbinding met MT5 succesvol gesloten")
                else:
                    self.logger.warning(
                        "Kon verbinding met MT5 mogelijk niet correct sluiten"
                    )
        except Exception as e:
            self.logger.error(f"Fout bij afsluiten verbinding: {e}")

        self.logger.info("Sophia Trading System afgesloten")


def parse_arguments() -> None:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Sophia Trading Framework")

    # Mode selectie
    parser.add_argument(
        "--mode",
        choices=["live", "backtest"],
        default="live",
        help="Trading mode (live of backtest)",
    )

    # Configuratie
    parser.add_argument("--config", type=str,
                        help="Pad naar configuratiebestand")

    # Backtest opties (als mode=backtest)
    parser.add_argument(
        "--backtest-script",
        action="store_true",
        help="Start backtest script in plaats van live trading",
    )

    # Dashboard opties
    parser.add_argument("--dashboard", action="store_true",
                        help="Start het dashboard")

    return parser.parse_args()


def main() -> None:
    """Hoofdfunctie voor de Sophia trading applicatie"""
    args = parse_arguments()

    # Start het dashboard indien gevraagd
    if args.dashboard:
        from src.backtesting.dashboard import main as dashboard_main

        return dashboard_main()

    # Start het backtest script indien gevraagd
    if args.backtest_script:
        from src.backtesting.backtest import main as backtest_main

        return backtest_main()

    # Anders start normal trader
    trader = SophiaTrader(
        config_path=args.config, backtest_mode=(args.mode == "backtest")
    )
    return trader.run()


if __name__ == "__main__":
    sys.exit(main())

