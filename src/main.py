# src/main.py
import sys
import os
import time
import traceback
from datetime import datetime

# Voeg project root toe aan Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils import setup_logging, load_config
from src.connector import MT5Connector
from src.risk import RiskManager
from src.strategy import TurtleStrategy


def main():
    """Hoofdfunctie voor de Sophia trading applicatie"""
    # Setup logging
    logger = setup_logging()
    logger.info("====== Sophia Trading System ======")
    logger.info(f"Opgestart op {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Ensure config directory exists
    config_dir = os.path.join(project_root, "config")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "settings.json")

    # Create default config if it doesn't exist
    if not os.path.exists(config_path):
        logger.warning(
            f"Configuratiebestand niet gevonden op {config_path}, standaardconfiguratie wordt gebruikt")
        default_config = {"mt5": {"server": "Demo Server", "login": 12345678,
                                  "password": "demo_password", "timeout": 10000},
                          "risk": {"risk_per_trade": 0.01, "max_daily_loss": 0.05},
                          "strategy": {"atr_period": 14, "entry_atr_multiplier": 1.0,
                                       "exit_atr_multiplier": 2.0}, "symbols": ["EURUSD"], "interval": 60}

        try:
            import json
            with open(config_path, "w") as f:
                json.dump(default_config, f, indent=4)
            logger.info(f"Standaardconfiguratie aangemaakt op {config_path}")
        except Exception as e:
            logger.error(f"Kon standaardconfiguratie niet aanmaken: {e}")

    # Laad configuratie
    config = load_config(config_path)
    if not config:
        logger.error("Kon configuratie niet laden, stoppen...")
        return 1

    # Initialisatie van componenten met foutafhandeling
    try:
        # Maak componenten aan
        connector = MT5Connector(config.get("mt5", {}))

        # Verbinding maken met MT5
        connect_attempts = 0
        max_attempts = 3
        while connect_attempts < max_attempts:
            if connector.connect():
                break
            connect_attempts += 1
            logger.warning(
                f"Poging {connect_attempts}/{max_attempts} om verbinding te maken met MT5 mislukt. Opnieuw proberen...")
            time.sleep(5)

        if connect_attempts >= max_attempts:
            logger.error(
                "Kon geen verbinding maken met MT5 na meerdere pogingen, stoppen...")
            return 1

        # Haal account informatie op van MT5 in plaats van hardcoded waarde
        try:
            account_info = connector.get_account_info()
            if not account_info or "balance" not in account_info:
                logger.warning(
                    "Kon account informatie niet ophalen, gebruik standaard waarden")
                account_info = {"balance": 10000, "currency": "USD"}
        except Exception as e:
            logger.error(f"Fout bij ophalen account informatie: {e}")
            account_info = {"balance": 10000, "currency": "USD"}

        logger.info(
            f"Account balans: {account_info['balance']} {account_info.get('currency', '')}")

        # Initialiseer risicomanager en strategie
        risk_manager = RiskManager(config.get("risk", {}))
        strategy = TurtleStrategy(connector, risk_manager, config.get("strategy", {}))

        # Zorg ervoor dat positions dictionary bestaat
        if not hasattr(strategy, "positions") or strategy.positions is None:
            strategy.positions = {}

    except Exception as e:
        logger.error(f"Fout bij initialisatie componenten: {e}")
        logger.debug(traceback.format_exc())
        return 1

    # Trading loop
    try:
        symbols = config.get("symbols", ["EURUSD"])
        logger.info(f"Start trading voor symbolen: {symbols}")

        running = True
        last_run_time = time.time()

        while running:
            start_time = time.time()

            try:
                # Verwerk alle symbolen
                for symbol in symbols:
                    try:
                        # Check voor signalen
                        result = strategy.check_signals(symbol)

                        if result and result.get("signal"):
                            signal = result["signal"]
                            meta = result.get("meta", {})

                            if signal in ["BUY", "SELL"]:
                                entry_price = meta.get("entry_price", 0)
                                stop_loss = meta.get("stop_loss", 0)

                                # Valideer entry en stop-loss
                                if entry_price <= 0 or stop_loss <= 0:
                                    logger.warning(
                                        f"Ongeldige entry of stop-loss voor {symbol}: Entry={entry_price}, SL={stop_loss}")
                                    continue

                                # Bereken positiegrootte
                                position_size = risk_manager.calculate_position_size(
                                    account_info["balance"], entry_price, stop_loss)

                                if position_size <= 0:
                                    logger.warning(
                                        f"Ongeldige positiegrootte berekend voor {symbol}: {position_size}")
                                    continue

                                # Probeer order te plaatsen
                                try:
                                    # Hier zou een echte order plaatsingscode komen
                                    # order_result = connector.place_order(symbol, signal, position_size, entry_price, stop_loss)
                                    order_result = {"success": True,
                                                    "order_id": 12345}  # Placeholder

                                    if order_result and order_result.get("success"):
                                        logger.info(
                                            f"Order geplaatst: {signal} {position_size} lots {symbol} @ "
                                            f"{entry_price} SL: {stop_loss}")

                                        # Update positie tracking
                                        strategy.positions[symbol] = {
                                            "direction": signal,
                                            "entry_price": entry_price,
                                            "stop_loss": stop_loss,
                                            "size": position_size,
                                            "entry_time": datetime.now(),
                                            "order_id": order_result.get("order_id")}
                                    else:
                                        logger.error(
                                            f"Order plaatsen mislukt voor {symbol}: {order_result}")
                                except Exception as e:
                                    logger.error(
                                        f"Fout bij order plaatsen voor {symbol}: {e}")

                            elif signal in ["CLOSE_BUY", "CLOSE_SELL"]:
                                if symbol in strategy.positions:
                                    try:
                                        # Hier zou een echte ordersluitingscode komen
                                        # close_result = connector.close_position(symbol, strategy.positions[symbol])
                                        close_result = {"success": True}  # Placeholder

                                        if close_result and close_result.get("success"):
                                            logger.info(f"Positie gesloten: {symbol}")
                                            # Verwijder positie uit tracking
                                            del strategy.positions[symbol]
                                        else:
                                            logger.error(
                                                f"Positie sluiten mislukt voor {symbol}: {close_result}")
                                    except Exception as e:
                                        logger.error(
                                            f"Fout bij sluiten positie voor {symbol}: {e}")
                    except Exception as e:
                        logger.error(f"Fout bij verwerken signalen voor {symbol}: {e}")
                        logger.debug(traceback.format_exc())

                # Wacht voor volgende iteratie, gecorrigeerd voor verwerkingstijd
                interval = config.get("interval", 60)  # Seconden
                elapsed = time.time() - start_time
                wait_time = max(0.1,
                                interval - elapsed)  # Minimaal 0.1 seconden wachten

                logger.info(f"Wacht {wait_time:.1f} seconden tot volgende check...")
                time.sleep(wait_time)

            except Exception as e:
                logger.error(f"Onverwachte fout in hoofdloop: {e}")
                logger.debug(traceback.format_exc())
                # Kleine pauze om CPU-verbruik te beperken bij herhaalde fouten
                time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Programma gestopt door gebruiker")
    except Exception as e:
        logger.critical(f"Kritieke fout in programma: {e}")
        logger.debug(traceback.format_exc())
    finally:
        # Sluit verbinding en maak resources vrij
        try:
            if connector:
                disconnect_success = connector.disconnect()
                if disconnect_success:
                    logger.info("Verbinding met MT5 succesvol gesloten")
                else:
                    logger.warning(
                        "Kon verbinding met MT5 mogelijk niet correct sluiten")
        except Exception as e:
            logger.error(f"Fout bij afsluiten verbinding: {e}")

        logger.info("Sophia Trading System afgesloten")

    return 0


if __name__ == "__main__":
    sys.exit(main())