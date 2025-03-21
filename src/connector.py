# src/connector.py
import logging
import os
from typing import Optional, Dict, Any, List

import MetaTrader5 as mt5
import pandas as pd

# Constants for timeframes
TIMEFRAMES = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}


class MT5Connector:
    """
    MetaTrader 5 connector voor het ophalen van marktdata en uitvoeren van orders.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialiseer de MT5 connector.

        Args:
            config: Dictionary met MT5 verbindingsinstellingen
        """
        self.config = config
        self.logger = logging.getLogger("sophia")
        self.connected = False
        self.tf_map = TIMEFRAMES

    def _validate_mt5_path(self) -> bool:
        """
        Valideert het MT5 installatiepath en probeert alternatieven als het huidige pad niet werkt.

        Returns:
            bool: True als een werkend pad is gevonden, anders False
        """
        current_path = self.config.get("mt5_path", "")

        # Als het huidige pad werkt, gebruik het
        if current_path and os.path.exists(current_path):
            return True

        # Lijst met mogelijke installatiepaden
        common_paths = [
            r"C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe",
            r"C:\Program Files\MetaTrader 5\terminal64.exe",
            r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe"]

        # Probeer alternatieve paden
        for path in common_paths:
            if os.path.exists(path):
                self.logger.info(f"MT5 installatie gevonden op: {path}")
                self.config["mt5_path"] = path
                return True

        self.logger.error("Geen geldige MT5 installatie gevonden")
        return False

    def connect(self) -> bool:
        """
        Verbind met het MT5 platform.

        Returns:
            bool: True als verbinding succesvol is, False indien niet
        """
        if self.connected:
            return True

        # Valideer MT5 pad
        if not self._validate_mt5_path():
            return False

        # Initialize MT5
        mt5_path = self.config.get("mt5_path", "")
        self.logger.info(f"Verbinden met MT5 op pad: {mt5_path}")

        if not mt5.initialize(path=mt5_path):
            self.logger.error(f"MT5 initialisatie mislukt: {mt5.last_error()}")
            return False

        # Login to MT5
        login = self.config.get("login", 0)
        password = self.config.get("password", "")
        server = self.config.get("server", "")

        if not mt5.login(login=login, password=password, server=server):
            self.logger.error(f"MT5 login mislukt: {mt5.last_error()}")
            self._shutdown_mt5()
            return False

        self.connected = True
        self.logger.info("Succesvol verbonden met MT5")
        return True

    def disconnect(self) -> bool:
        """
        Verbreek verbinding met het MT5 platform.

        Returns:
            bool: True als verbinding succesvol verbroken is
        """
        if self.connected:
            self._shutdown_mt5()
            self.logger.info("Verbinding met MT5 verbroken")
            return True
        return False

    def _shutdown_mt5(self) -> None:
        """
        Sluit de MT5 verbinding veilig af.
        """
        mt5.shutdown()
        self.connected = False

    def get_historical_data(self, symbol: str, timeframe: str, bars_count: int = 100) -> \
    Optional[pd.DataFrame]:
        """
        Haal historische prijsdata op van MT5.

        Args:
            symbol: Het handelsinstrument symbool (bijv. "EURUSD")
            timeframe: De timeframe als string (bijv. "M1", "H1", "D1")
            bars_count: Aantal bars om op te halen

        Returns:
            pd.DataFrame: DataFrame met historische data of None als ophalen mislukt
        """
        if not self.connected and not self.connect():
            return None

        # Converteer timeframe string naar MT5 constante
        tf = self.tf_map.get(timeframe, mt5.TIMEFRAME_D1)

        # Haal data op
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars_count)
        if rates is None or len(rates) == 0:
            self.logger.error(f"Geen data ontvangen voor {symbol}")
            return None

        # Converteer naar DataFrame en formatteer tijd
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_account_info(self) -> Dict[str, Any]:
        """
        Haalt account informatie op van MT5.

        Returns:
            Dict[str, Any]: Dictionary met account eigenschappen
        """
        if not self.connected and not self.connect():
            self.logger.error("Niet verbonden met MT5")
            return {}

        try:
            account_info = mt5.account_info()
            if not account_info:
                self.logger.error(
                    f"Kon account informatie niet ophalen: {mt5.last_error()}")
                return {}

            # Converteer account info naar een dictionary
            result = {"balance": account_info.balance, "equity": account_info.equity,
                "margin": account_info.margin, "free_margin": account_info.margin_free,
                "margin_level": account_info.margin_level if hasattr(account_info,
                                                                     "margin_level") else 0.0,
                "currency": account_info.currency}

            self.logger.info(
                f"Account info opgehaald: Balans={result['balance']} {result['currency']}")
            return result

        except Exception as e:
            self.logger.error(f"Fout bij ophalen account informatie: {e}")
            return {}

    def place_order(self, symbol: str, order_type: str, volume: float,
                    price: float = 0.0, sl: float = 0.0, tp: float = 0.0,
                    comment: str = "") -> Dict[str, Any]:
        """
        Plaatst een order in MT5.

        Args:
            symbol: Handelssymbool
            order_type: Type order ('BUY' of 'SELL')
            volume: Volume in lots
            price: Prijs (0 voor marktorders)
            sl: Stop loss prijs
            tp: Take profit prijs
            comment: Commentaar voor de order

        Returns:
            Dict met order details of error informatie
        """
        if not self.connected and not self.connect():
            self.logger.error("Niet verbonden met MT5")
            return {"success": False, "error": "Niet verbonden met MT5"}

        try:
            # Bepaal order type
            mt5_order_type = mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL

            # Haal symbool info op
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info or not symbol_info.visible:
                self.logger.error(f"Symbool {symbol} niet beschikbaar")
                return {"success": False, "error": f"Symbool {symbol} niet beschikbaar"}

            # Haal huidige prijs op als geen prijs is opgegeven
            if price <= 0:
                tick = mt5.symbol_info_tick(symbol)
                price = tick.ask if order_type == "BUY" else tick.bid

            # Stel order request samen
            request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol,
                "volume": float(volume), "type": mt5_order_type, "price": price,
                "sl": sl, "tp": tp, "deviation": 20, "magic": 123456,
                "comment": comment, "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC}

            # Verstuur order
            self.logger.info(
                f"Order versturen: {order_type} {volume} {symbol} @ {price} SL: {sl} TP: {tp}")
            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Order mislukt met code: {result.retcode}")
                return {"success": False, "error": f"Order mislukt: {result.retcode}"}

            # Order gelukt
            self.logger.info(f"Order geplaatst: Ticket #{result.order}")
            return {"success": True, "order_id": str(result.order), "symbol": symbol,
                "type": order_type, "volume": volume, "price": price, "sl": sl,
                "tp": tp}

        except Exception as e:
            self.logger.error(f"Fout bij plaatsen order: {e}")
            return {"success": False, "error": str(e)}

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Haalt informatie op over de huidige positie voor een symbool.

        Args:
            symbol: Handelssymbool

        Returns:
            Dict met positie informatie of None als er geen positie is
        """
        if not self.connected and not self.connect():
            return None

        try:
            positions = mt5.positions_get(symbol=symbol)
            if positions and len(positions) > 0:
                position = positions[0]
                return {"symbol": position.symbol,
                    "direction": "BUY" if position.type == 0 else "SELL",
                    "volume": position.volume, "open_price": position.price_open,
                    "current_price": position.price_current, "profit": position.profit,
                    "sl": position.sl, "tp": position.tp}
            return None

        except Exception as e:
            self.logger.error(f"Fout bij ophalen positie: {e}")
            return None

    def get_open_positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Haalt alle open posities op.

        Returns:
            Dict met symbolen als keys en lijsten van posities als values
        """
        if not self.connected and not self.connect():
            return {}

        try:
            all_positions = mt5.positions_get()
            result = {}

            if all_positions:
                for position in all_positions:
                    symbol = position.symbol
                    if symbol not in result:
                        result[symbol] = []

                    result[symbol].append(
                        {"direction": "BUY" if position.type == 0 else "SELL",
                            "volume": position.volume,
                            "open_price": position.price_open,
                            "current_price": position.price_current,
                            "profit": position.profit, "sl": position.sl,
                            "tp": position.tp})

            return result

        except Exception as e:
            self.logger.error(f"Fout bij ophalen open posities: {e}")
            return {}

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Sluit een open positie voor het opgegeven symbool.

        Args:
            symbol: Handelssymbool waarvoor de positie gesloten moet worden

        Returns:
            Dict met resultaat van de sluitingsoperatie
        """
        if not self.connected and not self.connect():
            self.logger.error("Niet verbonden met MT5")
            return {"success": False, "error": "Niet verbonden met MT5"}

        try:
            # Haal huidige positie op
            position = self.get_position(symbol)
            if not position:
                return {"success": False, "error": f"Geen open positie voor {symbol}"}

            # Bepaal tegengestelde order type voor sluiting
            close_type = "SELL" if position["direction"] == "BUY" else "BUY"

            # Haal huidige marktprijzen op
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return {"success": False,
                        "error": f"Kon prijsgegevens niet ophalen voor {symbol}"}

            # Gebruik ask voor BUY en bid voor SELL
            close_price = tick.ask if close_type == "BUY" else tick.bid

            # Stel order request samen voor het sluiten van de positie
            request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol,
                "volume": position["volume"],
                "type": mt5.ORDER_TYPE_BUY if close_type == "BUY" else mt5.ORDER_TYPE_SELL,
                "position": int(position.get("ticket", 0)),
                # Ticket ID van de te sluiten positie
                "price": close_price, "deviation": 20, "magic": 123456,
                "comment": f"Sophia sluiting {position['direction']} positie",
                "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}

            # Verstuur sluitingsorder
            self.logger.info(
                f"Positie sluiten: {symbol} {position['direction']} {position['volume']} lots")
            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Positie sluiten mislukt met code: {result.retcode}")
                return {"success": False,
                        "error": f"Positie sluiten mislukt: {result.retcode}"}

            self.logger.info(f"Positie gesloten: {symbol} - Ticket #{result.order}")
            return {"success": True, "order_id": str(result.order), "symbol": symbol,
                "closed_volume": position["volume"], "close_price": close_price}

        except Exception as e:
            self.logger.error(f"Fout bij sluiten positie: {e}")
            return {"success": False, "error": str(e)}

    def get_available_symbols(self) -> List[str]:
        """
        Haalt de lijst met beschikbare handelssymbolen op.

        Returns:
            List[str]: Lijst met beschikbare symbolen
        """
        if not self.connected and not self.connect():
            return []

        try:
            # Haal alle symbolen op
            symbols = mt5.symbols_get()
            if not symbols:
                self.logger.warning("Geen symbolen gevonden")
                return []

            # Filter op forex symbolen (als voorbeeld)
            forex_symbols = [symbol.name for symbol in symbols if symbol.visible and (
                        len(symbol.name) == 6 or "/" in symbol.name)]

            return forex_symbols

        except Exception as e:
            self.logger.error(f"Fout bij ophalen beschikbare symbolen: {e}")
            return []