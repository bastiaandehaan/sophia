#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced FTMO MT5 Broker Analyzer
---------------------------------
Analyzes broker specifications for MetaTrader 5 with focus on FTMO rules.
Provides a compact summary of trading conditions and FTMO-specific limits
that can be used to configure automated trading systems.
"""

import json
import os
import sys

import MetaTrader5 as mt5
import pandas as pd
from tabulate import tabulate


class MT5BrokerAnalyzer:
    """Compact class for analyzing MT5 broker conditions with FTMO focus."""

    def __init__(self, terminal_path=None):
        """Initialize the analyzer and connect to MT5."""
        self.mt5_connected = False
        self.account_info = None
        self.terminal_info = None
        self.ftmo_rules = self._load_ftmo_rules()

        # Try to connect
        if terminal_path and os.path.exists(terminal_path):
            self.mt5_connected = self.connect_to_mt5(terminal_path)
        else:
            # Try without path first
            self.mt5_connected = self.connect_to_mt5()
            if not self.mt5_connected:
                # Look for standard paths
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
            # Get basic information
            self.terminal_info = mt5.terminal_info()._asdict()
            self.account_info = mt5.account_info()._asdict()

    def _load_ftmo_rules(self):
        """Load FTMO rules from a predefined dictionary."""
        # These are the key FTMO rules that need to be respected by trading bots
        return {
            "daily_loss_limit": 0.05,  # 5% of account balance
            "max_loss_limit": 0.10,  # 10% of account balance
            "profit_targets": {
                "normal": 0.10,  # 10% profit target for normal accounts
                "aggressive": 0.20,  # 20% profit target for aggressive accounts
                "swing": 0.10  # 10% profit target for swing accounts
            },
            "min_trading_days": 10,
            # Minimum trading days for Challenge/Verification
            "max_daily_trading_hours": 8,
            # Recommended maximum daily trading hours
            "weekend_trading": False,  # No weekend trading allowed
            "prohibited_trading": [
                "News exploitation",  # Trading around major news events
                "Hedging",  # Simultaneous opposite positions
                "Symbol arbitrage",  # Exploiting price differences
                "Gap trading",  # Trading before major gaps
                "EA without stops",  # Trading without stop losses
                "Overnight positions without stop loss"  # Self-explanatory
            ],
            "position_holding": {
                "normal": "No restrictions",
                "aggressive": "No restrictions",
                "swing": "Must hold overnight"
                # Swing accounts must hold positions overnight
            }
        }

    def connect_to_mt5(self, path=None):
        """Connect to MT5 terminal."""
        print("\n=== MT5 CONNECTION ===")

        # Initialize MT5
        try:
            # If path is None, don't use the path parameter
            if path:
                if not mt5.initialize(path=path):
                    print(
                        f"Initialize() failed, error code = {mt5.last_error()}")
                    return False
            else:
                if not mt5.initialize():
                    print(
                        f"Initialize() failed, error code = {mt5.last_error()}")
                    return False

            # Check connection
            terminal = mt5.terminal_info()
            if not terminal:
                print(
                    f"Could not connect to terminal, error code = {mt5.last_error()}")
                return False

            # Print basic information
            terminal_dict = terminal._asdict()
            account = mt5.account_info()

            if account and terminal:
                print(f"Terminal: {terminal_dict.get('name', 'Unknown')}")
                print(f"Build: {terminal_dict.get('build', 'Unknown')}")
                print(f"Connected to account: {account.login}")
                print(f"Server: {account.server}")
                print(f"Balance: {account.balance:.2f} {account.currency}")
                print(f"Leverage: 1:{account.leverage}")
                return True
        except Exception as e:
            print(f"Error connecting to MT5: {e}")

        return False

    def print_account_details(self):
        """Print expanded account information."""
        if not self.mt5_connected or not self.account_info:
            print("No connection to MT5 or account info available.")
            return

        print("\n=== ACCOUNT DETAILS ===")

        # Basic account information
        details = [
            ["Login", self.account_info['login']],
            ["Name", self.account_info['name']],
            ["Server", self.account_info['server']],
            ["Currency", self.account_info['currency']],
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

        # Account type detection (FTMO, prop firm, etc.)
        account_type = self.detect_account_type()
        details.append(["Account Type", account_type])

        # Trading allowed status
        details.append(["Trading Allowed",
                        "Yes" if self.terminal_info.get('trade_allowed',
                                                        False) else "No"])

        # Print the table
        print(tabulate(details, tablefmt="simple"))

    def detect_account_type(self):
        """Detect the account type (FTMO, prop firm, demo, etc.)."""
        if not self.account_info:
            return "Unknown"

        server = self.account_info['server'].lower()
        name = self.account_info['name'].lower()

        # FTMO detection
        if 'ftmo' in server or 'ftmo' in name:
            if 'challenge' in name:
                return "FTMO Challenge"
            elif 'verification' in name:
                return "FTMO Verification"
            elif 'trial' in name or 'demo' in server:
                return "FTMO Free Trial"
            else:
                return "FTMO Funded Account"

        # Other prop firms
        if any(
            x in server or x in name for x in ['prop', 'funded', 'evaluation']):
            return "Proprietary Trading Account"

        # Standard types
        if 'demo' in server:
            return "Demo Account"
        elif 'contest' in server:
            return "Contest Account"

        return "Live Account"

    def get_trading_instruments(self, categories=None):
        """Get available trading instruments."""
        if not self.mt5_connected:
            print("Not connected to MT5.")
            return pd.DataFrame()

        # Get all symbols
        symbols = mt5.symbols_get()
        if not symbols:
            print(f"No symbols found. Error: {mt5.last_error()}")
            return pd.DataFrame()

        # Filter by categories if specified
        if categories:
            filtered_symbols = []
            for s in symbols:
                if hasattr(s, 'path') and any(
                    cat.lower() in s.path.lower() for cat in categories):
                    filtered_symbols.append(s)
            symbols = filtered_symbols

        # Collect relevant information
        symbols_data = []
        for s in symbols:
            # Get only essential data
            symbol_data = {
                'name': s.name,
                'description': s.description,
                'path': getattr(s, 'path', 'Unknown'),  # Category
                'spread': s.spread,
                'trade_mode': self.translate_trade_mode(s.trade_mode),
                'contract_size': s.trade_contract_size,
                'volume_min': s.volume_min,
                'volume_max': s.volume_max,
                'volume_step': s.volume_step
            }

            # Add optional fields if available
            if hasattr(s, 'margin_initial'):
                symbol_data['margin_initial'] = s.margin_initial
            if hasattr(s, 'currency_base'):
                symbol_data['currency_base'] = s.currency_base
            if hasattr(s, 'currency_profit'):
                symbol_data['currency_profit'] = s.currency_profit

            symbols_data.append(symbol_data)

        return pd.DataFrame(symbols_data)

    def print_ftmo_rules(self):
        """Print FTMO-specific trading rules."""
        print("\n=== FTMO TRADING RULES ===")

        # Format data for tabular display
        rules_data = [
            ["Daily Loss Limit",
             f"{self.ftmo_rules['daily_loss_limit'] * 100}% of account balance"],
            ["Max Loss Limit",
             f"{self.ftmo_rules['max_loss_limit'] * 100}% of account balance"],
            ["Normal Profit Target",
             f"{self.ftmo_rules['profit_targets']['normal'] * 100}% of account"],
            ["Aggressive Profit Target",
             f"{self.ftmo_rules['profit_targets']['aggressive'] * 100}% of account"],
            ["Swing Profit Target",
             f"{self.ftmo_rules['profit_targets']['swing'] * 100}% of account"],
            ["Min Trading Days",
             f"{self.ftmo_rules['min_trading_days']} days (Challenge/Verification)"],
            ["Max Daily Trading",
             f"{self.ftmo_rules['max_daily_trading_hours']} hours recommended"],
            ["Weekend Trading", "Not allowed"],
            ["Position Holding (Swing)", "Must hold positions overnight"]
        ]

        print(tabulate(rules_data, tablefmt="simple"))

        print("\n--- Prohibited Trading Practices ---")
        for i, practice in enumerate(self.ftmo_rules['prohibited_trading'], 1):
            print(f"{i}. {practice}")

    def print_automated_trading_requirements(self):
        """Print requirements specific for automated trading systems."""
        account_type = self.detect_account_type()
        is_ftmo = 'ftmo' in account_type.lower()
        balance = self.account_info.get('balance',
                                        10000)  # Default if not available

        print("\n=== AUTOMATED TRADING REQUIREMENTS ===")

        # Risk management requirements
        risk_data = [
            ["Parameter", "Requirement", "Notes"],
            ["Stop Loss", "MANDATORY", "Every position must have a stop loss"],
            ["Max Risk Per Trade", "1-2% of balance",
             f"${balance * 0.01:.2f} - ${balance * 0.02:.2f}"],
            ["Daily Loss Limit",
             f"{self.ftmo_rules['daily_loss_limit'] * 100}% of balance",
             f"${balance * self.ftmo_rules['daily_loss_limit']:.2f}"],
            ["Total Loss Limit",
             f"{self.ftmo_rules['max_loss_limit'] * 100}% of balance",
             f"${balance * self.ftmo_rules['max_loss_limit']:.2f}"],
            ["Max Drawdown",
             f"{self.ftmo_rules['max_loss_limit'] * 100}% from initial",
             "Must terminate trading if reached"],
            ["Position Sizing", "Adaptive",
             "Based on volatility & stop distance"],
            ["Correlation Check", "Recommended",
             "Avoid multiple correlated positions"]
        ]

        print(tabulate(risk_data, headers="firstrow", tablefmt="grid"))

        # Trading behavior requirements
        behavior_data = [
            ["Parameter", "Requirement"],
            ["Trading Hours", "Regular market hours (avoid low liquidity)"],
            ["News Trading", "Avoid major news events"],
            ["Trading Frequency", "Monitor daily transaction limits"],
            ["Weekend Positions", "Close or strongly secure before weekend"],
            ["Error Handling", "Robust error recovery mechanism"],
            ["Connection Loss", "Automatic shutdown/restart protocols"]
        ]

        print("\n--- Trading Bot Behavior ---")
        print(tabulate(behavior_data, headers="firstrow", tablefmt="simple"))

        # Specific guidance for EA operation
        print("\n--- Trading Bot Configuration Guidelines ---")
        if is_ftmo:
            print("1. Implement absolute loss limits (both daily and total)")
            print(
                "2. Enforce strict risk management regardless of strategy confidence")
            print(
                "3. Include time-based position management (especially for Swing accounts)")
            print("4. Avoid trading during major economic news events")
            print("5. Implement defensive overnight position handling")
            print("6. Monitor multiple timeframes to avoid overtrading")
            print("7. Create detailed trade logs for FTMO compliance checks")
        else:
            print("1. Apply standard risk management principles")
            print(
                "2. Consider broker-specific transaction fees in calculations")
            print("3. Adapt to account-specific margin requirements")
            print("4. Monitor broker trading hours and restrictions")

    def get_broker_limits(self):
        """Get broker-specific limits."""
        if not self.mt5_connected:
            print("Not connected to MT5.")
            return {}

        # FTMO and other prop firms usually have specific limits
        account_type = self.detect_account_type()

        # Get general limits
        limits = {
            "Account Type": account_type,
            "Max Orders": self.account_info.get('limit_orders', 'Unknown'),
            "Leverage": f"1:{self.account_info.get('leverage', 'Unknown')}",
            "Balance": f"{self.account_info.get('balance', 0):.2f} {self.account_info.get('currency', '')}",
        }

        # Add FTMO-specific limits if available
        if 'ftmo' in account_type.lower():
            daily_loss = self.ftmo_rules['daily_loss_limit'] * 100
            max_loss = self.ftmo_rules['max_loss_limit'] * 100

            limits.update({
                "Daily Loss Limit": f"{daily_loss}% of account balance (${self.account_info.get('balance', 10000) * self.ftmo_rules['daily_loss_limit']:.2f})",
                "Max Loss Limit": f"{max_loss}% of account balance (${self.account_info.get('balance', 10000) * self.ftmo_rules['max_loss_limit']:.2f})",
                "Profit Target": "Varies by account level (10-20%)",
                "Min Trading Days": "10 days (for Challenge/Verification)",
                "Scaling Plan": "Available after consistent results"
            })

        # Determine trading hours
        limits["Trading Hours"] = "24/5 for most FX, varies by instrument"

        return limits

    def print_broker_limits(self):
        """Print broker-specific limits."""
        limits = self.get_broker_limits()
        if not limits:
            return

        print("\n=== BROKER LIMITS AND CONDITIONS ===")

        for key, value in limits.items():
            print(f"{key}: {value}")

    def get_popular_symbols(self, count=10):
        """Get the most popular symbols sorted by spread."""
        if not self.mt5_connected:
            print("Not connected to MT5.")
            return pd.DataFrame()

        # Try different categories
        try:
            # Get symbols from different categories
            forex = self.get_trading_instruments(categories=['forex'])
            indices = self.get_trading_instruments(
                categories=['index', 'indices', 'cash'])
            commodities = self.get_trading_instruments(
                categories=['commodit', 'metal'])
            crypto = self.get_trading_instruments(categories=['crypto'])

            # Combine and sort by spread
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
                # Fallback: get all symbols and filter by spread
                all_symbols = self.get_trading_instruments()
                all_symbols = all_symbols.sort_values('spread').head(count)

            # Select relevant columns
            columns = ['name', 'description', 'spread', 'trade_mode',
                       'contract_size']
            columns = [col for col in columns if col in all_symbols.columns]
            return all_symbols[columns].head(count).sort_values('spread')

        except Exception as e:
            print(f"Error getting popular symbols: {e}")
            # Fallback: get all symbols
            symbols = self.get_trading_instruments()
            if symbols.empty:
                return pd.DataFrame()

            columns = ['name', 'description', 'spread', 'trade_mode',
                       'contract_size']
            columns = [col for col in columns if col in symbols.columns]
            return symbols[columns].head(count).sort_values('spread')

    def print_popular_symbols(self, count=10):
        """Print the most popular symbols with their conditions."""
        symbols = self.get_popular_symbols(count)
        if symbols.empty:
            print("No symbols found.")
            return

        print(f"\n=== TOP {count} TRADING INSTRUMENTS ===")
        print(tabulate(symbols, headers='keys', tablefmt='simple',
                       showindex=False))

    def generate_bot_config(self, output_file="trading_bot_config.json"):
        """Generate a configuration file for a trading bot based on broker and FTMO rules."""
        account_type = self.detect_account_type()
        is_ftmo = 'ftmo' in account_type.lower()
        is_challenge = 'challenge' in account_type.lower()
        is_verification = 'verification' in account_type.lower()
        is_funded = 'funded' in account_type.lower() and not (
            is_challenge or is_verification)

        # Default values
        risk_per_trade = 0.01  # 1%
        max_daily_loss = self.ftmo_rules['daily_loss_limit']
        max_total_loss = self.ftmo_rules['max_loss_limit']

        # Adjust based on account type
        if is_ftmo:
            if is_challenge or is_verification:
                # Be slightly more conservative during evaluation
                risk_per_trade = 0.01  # 1%
            elif is_funded:
                # Can be slightly more aggressive with funded account
                risk_per_trade = 0.015  # 1.5%

        # Top instruments
        symbols_df = self.get_popular_symbols(15)
        symbols_list = symbols_df[
            'name'].tolist() if not symbols_df.empty else ["EURUSD", "GBPUSD",
                                                           "USDJPY"]

        # Create configuration
        config = {
            "mt5": {
                "server": self.account_info.get('server', 'FTMO-Demo'),
                "login": self.account_info.get('login', 0),
                "password": "",  # Leave blank for security
                "path": "C:\\Program Files\\FTMO Global Markets MT5 Terminal\\terminal64.exe",
            },
            "risk_management": {
                "risk_per_trade": risk_per_trade,
                "max_daily_loss": max_daily_loss,
                "max_total_loss": max_total_loss,
                "max_positions": 5,
                "max_correlated_positions": 2,
                "enforce_stop_loss": True,
                "adaptive_position_sizing": True
            },
            "trading_rules": {
                "trading_hours": {
                    "start": 8,  # 8 AM UTC
                    "end": 20,  # 8 PM UTC
                    "use_time_filter": True
                },
                "account_type": account_type,
                "is_ftmo": is_ftmo,
                "weekend_trading": False,
                "avoid_news_trading": True,
                "min_trading_days": self.ftmo_rules['min_trading_days'] if (
                    is_challenge or is_verification) else 0
            },
            "symbols": symbols_list[:5],  # Limit to top 5 by default
            "timeframes": ["H1", "H4", "D1"],  # Default timeframes
            "strategies": {
                "default": "turtle",  # Default strategy
                "turtle": {
                    "entry_period": 20,
                    "exit_period": 10,
                    "atr_period": 14,
                    "use_vol_filter": True
                },
                "ema": {
                    "fast_ema": 9,
                    "slow_ema": 21,
                    "signal_ema": 5,
                    "rsi_period": 14
                }
            }
        }

        # Save to file
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=4)

        print(f"\nTrading bot configuration saved to: {output_file}")
        return config

    def print_summary_report(self):
        """Print a summary report of broker conditions."""
        if not self.mt5_connected:
            print("Not connected to MT5.")
            return

        # Header
        print("\n" + "=" * 80)
        print("BROKER AND FTMO TRADING CONDITIONS SUMMARY".center(80))
        print("=" * 80)

        # Account info
        self.print_account_details()

        # FTMO rules (most important for trading bots)
        self.print_ftmo_rules()

        # Automated trading requirements
        self.print_automated_trading_requirements()

        # Broker limits
        self.print_broker_limits()

        # Top trading instruments
        self.print_popular_symbols(15)

        # Symbol specifications examples
        for symbol in ['EURUSD', 'GBPUSD', 'XAUUSD']:
            if mt5.symbol_info(symbol):
                self.print_symbol_specifications(symbol)

        # Generate trading bot configuration
        self.generate_bot_config()

        print("\n" + "=" * 80)
        print("END OF REPORT".center(80))
        print("=" * 80)

    def get_symbol_specifications(self, symbol):
        """Get detailed specifications for a symbol."""
        if not self.mt5_connected:
            print("Not connected to MT5.")
            return None

        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            print(f"Symbol '{symbol}' not found.")
            return None

        # Get tick info
        tick = mt5.symbol_info_tick(symbol)

        # Create structured view
        specs = {
            "Basic Info": {
                "Name": symbol_info.name,
                "Description": symbol_info.description,
                "ISIN": getattr(symbol_info, "isin", ""),
                "Category": getattr(symbol_info, "path", "Unknown"),
                "Base Currency": getattr(symbol_info, "currency_base", ""),
                "Profit Currency": getattr(symbol_info, "currency_profit", "")
            },
            "Trading Conditions": {
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
            "Swaps & Costs": {
                "Swap Long": symbol_info.swap_long,
                "Swap Short": symbol_info.swap_short,
                "Swap Rollover 3-days": symbol_info.swap_rollover3days,
                "Swap Mode": self.translate_swap_mode(
                    getattr(symbol_info, "swap_mode", 0))
            },
            "Price Information": {
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
            "Order Restrictions": {
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
        """Print detailed specifications for a symbol."""
        specs = self.get_symbol_specifications(symbol)
        if not specs:
            return

        print(f"\n=== SPECIFICATIONS FOR {symbol} ===")

        for section, details in specs.items():
            print(f"\n{section}:")
            for key, value in details.items():
                print(f"  {key}: {value}")

    # Translation helper functions for mt5 constants
    def translate_trade_mode(self, mode):
        """Translate trade mode code to readable text."""
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
        """Translate order mode to readable text."""
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
        """Translate filling mode to readable text."""
        try:
            result = []
            if mode & mt5.SYMBOL_FILLING_FOK: result.append("Fill or Kill")
            if mode & mt5.SYMBOL_FILLING_IOC: result.append(
                "Immediate or Cancel")
            return ", ".join(result) if result else "None"
        except Exception:
            return f"Mode {mode}"

    def translate_expiration_mode(self, mode):
        """Translate expiration mode to readable text."""
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
        """Translate swap mode to readable text."""
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
        """Close connection to MT5."""
        if self.mt5_connected:
            mt5.shutdown()
            self.mt5_connected = False
            print("MT5 connection closed.")


def main():
    """Main function for running the broker analysis."""
    print("Enhanced FTMO MT5 Broker Analyzer v2.0")
    print("-------------------------------------")

    # Terminal path
    terminal_path = None
    if len(sys.argv) > 1:
        terminal_path = sys.argv[1]
        print(f"Using terminal path: {terminal_path}")

    # Initialize analyzer
    analyzer = MT5BrokerAnalyzer(terminal_path)

    if analyzer.mt5_connected:
        # Print report
        analyzer.print_summary_report()
    else:
        print(
            "Could not connect to MT5. Make sure MT5 is installed and running.")

    # Close connection
    analyzer.shutdown()


if __name__ == "__main__":
    main()
