#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Verbeterde MT5 Broker Analyzer
----------------------------
Analyseert broker voorwaarden en symboolspecificaties voor MetaTrader 5.
Gericht op het tonen van FTMO en andere prop firm handelsvoorwaarden.
"""

import MetaTrader5 as mt5
import pandas as pd
import os
import sys
from datetime import datetime
from tabulate import tabulate


class MT5BrokerAnalyzer:
    """Compacte klasse voor het analyseren van MT5 broker voorwaarden."""

    def __init__(self, terminal_path=None):
        """Initialiseert de analyzer en maakt verbinding met MT5."""
        self.mt5_connected = False
        self.account_info = None
        self.terminal_info = None

        # Probeer verbinding te maken
        if terminal_path and os.path.exists(terminal_path):
            self.mt5_connected = self.connect_to_mt5(terminal_path)
        else:
            # Probeer eerst zonder pad
            self.mt5_connected = self.connect_to_mt5()
            if not self.mt5_connected:
                # Zoek naar standaard paden
                standard_paths = [
                    "C:\\Program Files\\FTMO Global Markets MT5 Terminal\\terminal64.exe",
                    "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
                ]
                for path in standard_paths:
                    if os.path.exists(path):
                        self.mt5_connected = self.connect_to_mt5(path)
                        if self.mt5_connected:
                            break

        if self.mt5_connected:
            # Basisinformatie ophalen
            self.terminal_info = mt5.terminal_info()._asdict()
            self.account_info = mt5.account_info()._asdict()

    def connect_to_mt5(self, path=None):
        """Maakt verbinding met MT5 terminal."""
        print("\n=== VERBINDING MET MT5 ===")

        # Initialiseer MT5
        try:
            # Als path None is, gebruik geen path parameter
            if path:
                if not mt5.initialize(path=path):
                    print(
                        f"Initialize() mislukt, error code = {mt5.last_error()}")
                    return False
            else:
                if not mt5.initialize():
                    print(
                        f"Initialize() mislukt, error code = {mt5.last_error()}")
                    return False

            # Controleer verbinding
            terminal = mt5.terminal_info()
            if not terminal:
                print(
                    f"Kon geen verbinding maken met terminal, error code = {mt5.last_error()}")
                return False

            # Print basisinformatie
            terminal_dict = terminal._asdict()
            account = mt5.account_info()

            if account and terminal:
                print(f"Terminal: {terminal_dict.get('name', 'Unknown')}")
                print(f"Build: {terminal_dict.get('build', 'Unknown')}")
                print(f"Verbonden met account: {account.login}")
                print(f"Server: {account.server}")
                print(f"Balance: {account.balance:.2f} {account.currency}")
                print(f"Leverage: 1:{account.leverage}")
                return True
        except Exception as e:
            print(f"Fout bij verbinden met MT5: {e}")

        return False

    def print_account_details(self):
        """Print uitgebreide accountinformatie."""
        if not self.mt5_connected or not self.account_info:
            print("Geen verbinding met MT5 of accountinfo beschikbaar.")
            return

        print("\n=== ACCOUNT DETAILS ===")

        # Basis accountinformatie
        details = [
            ["Login", self.account_info['login']],
            ["Naam", self.account_info['name']],
            ["Server", self.account_info['server']],
            ["Valuta", self.account_info['currency']],
            ["Leverage", f"1:{self.account_info['leverage']}"],
            ["Balance",
             f"{self.account_info['balance']:.2f} {self.account_info['currency']}"],
            ["Equity",
             f"{self.account_info['equity']:.2f} {self.account_info['currency']}"],
            ["Margin",
             f"{self.account_info['margin']:.2f} {self.account_info['currency']}"],
            ["Free Margin",
             f"{self.account_info['margin_free']:.2f} {self.account_info['currency']}"],
            ["Margin Level", f"{self.account_info['margin_level']:.2f}%"],
            ["Max Orders", self.account_info['limit_orders']]
        ]

        # Account type detectie (FTMO, prop firm, etc.)
        account_type = self.detect_account_type()
        details.append(["Account Type", account_type])

        # Trading allowed status
        details.append(["Trading Allowed",
                        "Yes" if self.terminal_info.get('trade_allowed',
                                                        False) else "No"])

        # Print tabel
        print(tabulate(details, tablefmt="simple"))

    def detect_account_type(self):
        """Detecteert het type account (FTMO, prop firm, demo, etc.)."""
        if not self.account_info:
            return "Unknown"

        server = self.account_info['server'].lower()
        name = self.account_info['name'].lower()

        # FTMO detectie
        if 'ftmo' in server or 'ftmo' in name:
            if 'challenge' in name:
                return "FTMO Challenge"
            elif 'verification' in name:
                return "FTMO Verification"
            elif 'trial' in name or 'demo' in server:
                return "FTMO Free Trial"
            else:
                return "FTMO Funded Account"

        # Andere prop firms
        if any(
            x in server or x in name for x in ['prop', 'funded', 'evaluation']):
            return "Proprietary Trading Account"

        # Standaard types
        if 'demo' in server:
            return "Demo Account"
        elif 'contest' in server:
            return "Contest Account"

        return "Live Account"

    def get_trading_instruments(self, categories=None):
        """Haalt beschikbare handelsinstrumenten op."""
        if not self.mt5_connected:
            print("Niet verbonden met MT5.")
            return pd.DataFrame()

        # Haal alle symbolen op
        symbols = mt5.symbols_get()
        if not symbols:
            print(f"Geen symbolen gevonden. Error: {mt5.last_error()}")
            return pd.DataFrame()

        # Filter op categorieën indien opgegeven
        if categories:
            filtered_symbols = []
            for s in symbols:
                if hasattr(s, 'path') and any(
                    cat.lower() in s.path.lower() for cat in categories):
                    filtered_symbols.append(s)
            symbols = filtered_symbols

        # Verzamel relevante informatie
        symbols_data = []
        for s in symbols:
            # Haal alleen essentiële gegevens op
            symbol_data = {
                'name': s.name,
                'description': s.description,
                'path': getattr(s, 'path', 'Unknown'),  # Categorie
                'spread': s.spread,
                'trade_mode': self.translate_trade_mode(s.trade_mode),
                'contract_size': s.trade_contract_size,
                'volume_min': s.volume_min,
                'volume_max': s.volume_max,
                'volume_step': s.volume_step
            }

            # Voeg optionele velden toe indien beschikbaar
            if hasattr(s, 'margin_initial'):
                symbol_data['margin_initial'] = s.margin_initial
            if hasattr(s, 'currency_base'):
                symbol_data['currency_base'] = s.currency_base
            if hasattr(s, 'currency_profit'):
                symbol_data['currency_profit'] = s.currency_profit

            symbols_data.append(symbol_data)

        return pd.DataFrame(symbols_data)

    def get_symbol_specifications(self, symbol):
        """Haalt gedetailleerde specificaties op voor een symbool."""
        if not self.mt5_connected:
            print("Niet verbonden met MT5.")
            return None

        # Haal symbool info op
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            print(f"Symbool '{symbol}' niet gevonden.")
            return None

        # Haal tick info op
        tick = mt5.symbol_info_tick(symbol)

        # Maak gestructureerde weergave
        specs = {
            "Basis Info": {
                "Naam": symbol_info.name,
                "Beschrijving": symbol_info.description,
                "ISIN": getattr(symbol_info, "isin", ""),
                "Categorie": getattr(symbol_info, "path", "Unknown"),
                "Base Currency": getattr(symbol_info, "currency_base", ""),
                "Profit Currency": getattr(symbol_info, "currency_profit", "")
            },
            "Trading Voorwaarden": {
                "Contract Size": symbol_info.trade_contract_size,
                "Min Volume": symbol_info.volume_min,
                "Max Volume": symbol_info.volume_max,
                "Volume Step": symbol_info.volume_step,
                "Trade Mode": self.translate_trade_mode(symbol_info.trade_mode),
                "Initial Margin": getattr(symbol_info, "margin_initial",
                                          "Unknown"),
                "Maintenance Margin": getattr(symbol_info, "margin_maintenance",
                                              "Unknown")
            },
            "Swaps & Kosten": {
                "Swap Long": symbol_info.swap_long,
                "Swap Short": symbol_info.swap_short,
                "Swap Rollover 3-days": symbol_info.swap_rollover3days,
                "Swap Mode": self.translate_swap_mode(
                    getattr(symbol_info, "swap_mode", 0))
            },
            "Prijsinformatie": {
                "Digits": symbol_info.digits,
                "Point": symbol_info.point,
                "Tick Size": getattr(symbol_info, "trade_tick_size", "Unknown"),
                "Tick Value": getattr(symbol_info, "trade_tick_value",
                                      "Unknown"),
                "Bid": tick.bid if tick else None,
                "Ask": tick.ask if tick else None,
                "Spread": symbol_info.spread,
                "Spread Float": bool(symbol_info.spread_float)
            },
            "Order-beperkingen": {
                "Stops Level": getattr(symbol_info, "trade_stops_level",
                                       "Unknown"),
                "Freeze Level": getattr(symbol_info, "trade_freeze_level",
                                        "Unknown"),
                "Order Modes": self.translate_order_mode(
                    getattr(symbol_info, "order_mode", 0)),
                "Filling Modes": self.translate_filling_mode(
                    getattr(symbol_info, "filling_mode", 0)),
                "Expiration Modes": self.translate_expiration_mode(
                    getattr(symbol_info, "expiration_mode", 0))
            }
        }

        return specs

    def print_symbol_specifications(self, symbol):
        """Print gedetailleerde specificaties voor een symbool."""
        specs = self.get_symbol_specifications(symbol)
        if not specs:
            return

        print(f"\n=== SPECIFICATIES VOOR {symbol} ===")

        for section, details in specs.items():
            print(f"\n{section}:")
            for key, value in details.items():
                print(f"  {key}: {value}")

    def get_broker_limits(self):
        """Haalt broker-specifieke limieten op."""
        if not self.mt5_connected:
            print("Niet verbonden met MT5.")
            return {}

        # FTMO en andere prop firms hebben meestal specifieke limieten
        account_type = self.detect_account_type()

        # Haal algemene limieten op
        limits = {
            "Account Type": account_type,
            "Max Orders": self.account_info.get('limit_orders', 'Unknown'),
            "Leverage": f"1:{self.account_info.get('leverage', 'Unknown')}",
            "Balance": f"{self.account_info.get('balance', 0):.2f} {self.account_info.get('currency', '')}",
        }

        # Voeg FTMO-specifieke limieten toe indien beschikbaar
        if 'ftmo' in account_type.lower():
            # Deze waarden zijn voorbeelden - zouden van comments/names/beschrijvingen kunnen komen
            limits.update({
                "Daily Loss Limit": "5% van account balance",
                "Max Loss Limit": "10% van account balance",
                "Profit Target": "Varieert per account niveau",
                "Min Trading Days": "10 dagen (voor Challenge/Verification)",
                "Scaling Plan": "Beschikbaar na consistente resultaten"
            })

        # Bepaal trading hours
        limits["Trading Hours"] = "24/5 voor meeste FX, varieert per instrument"

        return limits

    def print_broker_limits(self):
        """Print broker-specifieke limieten."""
        limits = self.get_broker_limits()
        if not limits:
            return

        print("\n=== BROKER LIMIETEN EN VOORWAARDEN ===")

        for key, value in limits.items():
            print(f"{key}: {value}")

    def get_popular_symbols(self, count=10):
        """Haalt de meest populaire symbolen op, gesorteerd op spread."""
        if not self.mt5_connected:
            print("Niet verbonden met MT5.")
            return pd.DataFrame()

        # Probeer verschillende categorieën te halen
        try:
            # Haal symbolen van verschillende categorieën op
            forex = self.get_trading_instruments(categories=['forex'])
            indices = self.get_trading_instruments(
                categories=['index', 'indices', 'cash'])
            commodities = self.get_trading_instruments(
                categories=['commodit', 'metal'])
            crypto = self.get_trading_instruments(categories=['crypto'])

            # Combineer en sorteer op spread
            frames = []
            if not forex.empty:
                frames.append(forex.sort_values('spread').head(count // 2))
            if not indices.empty:
                frames.append(indices.sort_values('spread').head(count // 4))
            if not commodities.empty:
                frames.append(
                    commodities.sort_values('spread').head(count // 8))
            if not crypto.empty:
                frames.append(crypto.sort_values('spread').head(count // 8))

            if frames:
                all_symbols = pd.concat(frames)
            else:
                # Fallback: haal alle symbolen op en filter op spread
                all_symbols = self.get_trading_instruments()
                all_symbols = all_symbols.sort_values('spread').head(count)

            # Selecteer relevante kolommen
            columns = ['name', 'description', 'spread', 'trade_mode',
                       'contract_size']
            columns = [col for col in columns if col in all_symbols.columns]
            return all_symbols[columns].head(count).sort_values('spread')

        except Exception as e:
            print(f"Fout bij ophalen populaire symbolen: {e}")
            # Fallback: haal alle symbolen op
            symbols = self.get_trading_instruments()
            if symbols.empty:
                return pd.DataFrame()

            columns = ['name', 'description', 'spread', 'trade_mode',
                       'contract_size']
            columns = [col for col in columns if col in symbols.columns]
            return symbols[columns].head(count).sort_values('spread')

    def print_popular_symbols(self, count=10):
        """Print de meest populaire symbolen met hun voorwaarden."""
        symbols = self.get_popular_symbols(count)
        if symbols.empty:
            print("Geen symbolen gevonden.")
            return

        print(f"\n=== TOP {count} HANDELSINSTRUMENTEN ===")
        print(tabulate(symbols, headers='keys', tablefmt='simple',
                       showindex=False))

    def print_summary_report(self):
        """Print een samenvattend rapport van broker voorwaarden."""
        if not self.mt5_connected:
            print("Niet verbonden met MT5.")
            return

        # Header
        print("\n" + "=" * 80)
        print("BROKER VOORWAARDEN SAMENVATTING".center(80))
        print("=" * 80)

        # Account info
        self.print_account_details()

        # Broker limieten
        self.print_broker_limits()

        # Top handelsinstrumenten
        self.print_popular_symbols(15)

        # Voorbeelden van symbool specificaties voor belangrijke instrumenten
        for symbol in ['EURUSD', 'GBPUSD', 'XAUUSD']:
            if mt5.symbol_info(symbol):
                self.print_symbol_specifications(symbol)

        print("\n" + "=" * 80)
        print("EINDE RAPPORT".center(80))
        print("=" * 80)

    # Vertaal-hulpfuncties voor mt5 constanten
    def translate_trade_mode(self, mode):
        """Vertaalt trade mode code naar leesbare tekst."""
        try:
            modes = {
                mt5.SYMBOL_TRADE_MODE_DISABLED: "Disabled",
                mt5.SYMBOL_TRADE_MODE_LONGONLY: "Long Only",
                mt5.SYMBOL_TRADE_MODE_SHORTONLY: "Short Only",
                mt5.SYMBOL_TRADE_MODE_CLOSEONLY: "Close Only",
                mt5.SYMBOL_TRADE_MODE_FULL: "Full Access"
            }
            return modes.get(mode, f"Unknown ({mode})")
        except Exception:
            return f"Mode {mode}"

    def translate_order_mode(self, mode):
        """Vertaalt order mode naar leesbare tekst."""
        try:
            result = []
            if mode & mt5.SYMBOL_ORDER_MARKET: result.append("Market")
            if mode & mt5.SYMBOL_ORDER_LIMIT: result.append("Limit")
            if mode & mt5.SYMBOL_ORDER_STOP: result.append("Stop")
            if mode & mt5.SYMBOL_ORDER_STOP_LIMIT: result.append("Stop Limit")
            if mode & mt5.SYMBOL_ORDER_SL: result.append("Stop Loss")
            if mode & mt5.SYMBOL_ORDER_TP: result.append("Take Profit")
            return ", ".join(result) if result else "None"
        except Exception:
            return f"Mode {mode}"

    def translate_filling_mode(self, mode):
        """Vertaalt filling mode naar leesbare tekst."""
        try:
            result = []
            if mode & mt5.SYMBOL_FILLING_FOK: result.append("Fill or Kill")
            if mode & mt5.SYMBOL_FILLING_IOC: result.append(
                "Immediate or Cancel")
            return ", ".join(result) if result else "None"
        except Exception:
            return f"Mode {mode}"

    def translate_expiration_mode(self, mode):
        """Vertaalt expiration mode naar leesbare tekst."""
        try:
            result = []
            if mode & mt5.SYMBOL_EXPIRATION_GTC: result.append(
                "Good Till Cancelled")
            if mode & mt5.SYMBOL_EXPIRATION_DAY: result.append("Day")
            if mode & mt5.SYMBOL_EXPIRATION_SPECIFIED: result.append(
                "Specified")
            return ", ".join(result) if result else "None"
        except Exception:
            return f"Mode {mode}"

    def translate_swap_mode(self, mode):
        """Vertaalt swap mode naar leesbare tekst."""
        try:
            modes = {
                mt5.SYMBOL_SWAP_MODE_DISABLED: "Disabled",
                mt5.SYMBOL_SWAP_MODE_POINTS: "Points",
                mt5.SYMBOL_SWAP_MODE_CURRENCY_SYMBOL: "Currency Symbol",
                mt5.SYMBOL_SWAP_MODE_CURRENCY_MARGIN: "Currency Margin",
                mt5.SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT: "Currency Deposit",
                mt5.SYMBOL_SWAP_MODE_INTEREST_CURRENT: "Interest Current",
                mt5.SYMBOL_SWAP_MODE_INTEREST_OPEN: "Interest Open",
                mt5.SYMBOL_SWAP_MODE_REOPEN_CURRENT: "Reopen Current",
                mt5.SYMBOL_SWAP_MODE_REOPEN_BID: "Reopen Bid"
            }
            return modes.get(mode, f"Unknown ({mode})")
        except Exception:
            return f"Mode {mode}"

    def shutdown(self):
        """Sluit verbinding met MT5 af."""
        if self.mt5_connected:
            mt5.shutdown()
            self.mt5_connected = False
            print("MT5 verbinding afgesloten.")


def main():
    """Hoofdfunctie voor het uitvoeren van de broker analyse."""
    print("MT5 Broker Analyzer v1.0")
    print("-----------------------")

    # Terminal pad
    terminal_path = None
    if len(sys.argv) > 1:
        terminal_path = sys.argv[1]
        print(f"Using terminal path: {terminal_path}")

    # Initialiseer analyzer
    analyzer = MT5BrokerAnalyzer(terminal_path)

    if analyzer.mt5_connected:
        # Print rapport
        analyzer.print_summary_report()
    else:
        print(
            "Kon geen verbinding maken met MT5. Controleer of MT5 is geïnstalleerd en gestart.")

    # Sluit verbinding
    analyzer.shutdown()


if __name__ == "__main__":
    main()