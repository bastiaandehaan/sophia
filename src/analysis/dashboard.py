#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Eenvoudig dashboard voor Sophia Trading Framework.
Biedt een interface om backtest, optimalisatie, en live trading te beheren.
"""

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

# Zorg dat het project root path in sys.path zit voor imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class SophiaDashboard:
    """Sophia Trading Framework Dashboard."""

    def __init__(self, root):
        """
        Initialiseer het dashboard.

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Sophia Trading Framework Dashboard")

        # Stel window grootte in
        width = 800
        height = 650
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(width, height)

        # Configuratie laden
        self.config = self.load_config()

        # Tabbladen maken
        self.create_notebook()

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Gereed")
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_config(self):
        """
        Laad de configuratie uit settings.json.

        Returns:
            Dictionary met configuratie
        """
        config_path = os.path.join(project_root, "config", "settings.json")
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            messagebox.showwarning(
                "Configuratie laden", f"Kon configuratie niet laden: {e}"
            )
            return {}

    def save_config(self, config):
        """
        Sla configuratie op naar settings.json.

        Args:
            config: Dictionary met configuratie
        """
        config_path = os.path.join(project_root, "config", "settings.json")
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            self.show_status("Configuratie opgeslagen")
        except Exception as e:
            messagebox.showerror(
                "Configuratie opslaan", f"Kon configuratie niet opslaan: {e}"
            )

    def create_notebook(self):
        """Maak tabbladen voor de verschillende functies."""
        self.notebook = ttk.Notebook(self.root)

        # Tabbladen
        self.backtest_tab = ttk.Frame(self.notebook)
        self.optimize_tab = ttk.Frame(self.notebook)
        self.live_tab = ttk.Frame(self.notebook)
        self.config_tab = ttk.Frame(self.notebook)

        # Tabbladen toevoegen
        self.notebook.add(self.backtest_tab, text="Backtest")
        self.notebook.add(self.optimize_tab, text="Optimalisatie")
        self.notebook.add(self.live_tab, text="Live Trading")
        self.notebook.add(self.config_tab, text="Configuratie")

        self.notebook.pack(expand=1, fill=tk.BOTH, padx=5, pady=5)

        # Tabbladen vullen
        self.setup_backtest_tab()
        self.setup_optimize_tab()
        self.setup_live_tab()
        self.setup_config_tab()

    def setup_backtest_tab(self):
        """Stel het backtest tabblad in."""
        # Main frame
        main_frame = ttk.Frame(self.backtest_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Input frame links
        input_frame = ttk.LabelFrame(main_frame, text="Backtest Parameters")
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5,
                         pady=5)

        # Strategie selectie
        ttk.Label(input_frame, text="Strategie:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_strategy_var = tk.StringVar(value="turtle")
        strategy_combobox = ttk.Combobox(
            input_frame,
            textvariable=self.backtest_strategy_var,
            values=["turtle", "ema"],
            state="readonly",
        )
        strategy_combobox.grid(row=0, column=1, sticky=tk.W + tk.E, padx=5,
                               pady=5)
        strategy_combobox.bind("<<ComboboxSelected>>",
                               self.on_backtest_strategy_change)

        # Symbolen
        ttk.Label(input_frame, text="Symbolen:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        symbols = self.config.get("symbols", ["EURUSD", "USDJPY"])
        self.backtest_symbols_var = tk.StringVar(value=", ".join(symbols))
        ttk.Entry(input_frame, textvariable=self.backtest_symbols_var).grid(
            row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Timeframe
        ttk.Label(input_frame, text="Timeframe:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_timeframe_var = tk.StringVar(
            value=self.config.get("timeframe", "H4")
        )
        ttk.Combobox(
            input_frame,
            textvariable=self.backtest_timeframe_var,
            values=["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
            state="readonly",
        ).grid(row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Periode
        ttk.Label(input_frame, text="Periode:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_period_var = tk.StringVar(value="1y")
        ttk.Combobox(
            input_frame,
            textvariable=self.backtest_period_var,
            values=["1m", "3m", "6m", "1y", "2y", "5y"],
            state="readonly",
        ).grid(row=3, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Initieel kapitaal
        ttk.Label(input_frame, text="Initieel kapitaal:").grid(
            row=4, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_cash_var = tk.StringVar(value="10000")
        ttk.Entry(input_frame, textvariable=self.backtest_cash_var).grid(
            row=4, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Strategie parameters frame
        strat_frame = ttk.LabelFrame(main_frame, text="Strategie Parameters")
        strat_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5,
                         pady=5)

        # Maak frames voor verschillende strategieën
        self.turtle_params_frame = ttk.Frame(strat_frame)
        self.ema_params_frame = ttk.Frame(strat_frame)

        # Turtle parameters
        ttk.Label(self.turtle_params_frame, text="Entry Period:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_entry_period_var = tk.StringVar(value="20")
        ttk.Entry(
            self.turtle_params_frame,
            textvariable=self.backtest_entry_period_var
        ).grid(row=0, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        ttk.Label(self.turtle_params_frame, text="Exit Period:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_exit_period_var = tk.StringVar(value="10")
        ttk.Entry(
            self.turtle_params_frame, textvariable=self.backtest_exit_period_var
        ).grid(row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        ttk.Label(self.turtle_params_frame, text="ATR Period:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_atr_period_var = tk.StringVar(value="14")
        ttk.Entry(
            self.turtle_params_frame, textvariable=self.backtest_atr_period_var
        ).grid(row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # EMA parameters
        ttk.Label(self.ema_params_frame, text="Fast EMA:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_fast_ema_var = tk.StringVar(value="9")
        ttk.Entry(self.ema_params_frame,
                  textvariable=self.backtest_fast_ema_var).grid(
            row=0, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        ttk.Label(self.ema_params_frame, text="Slow EMA:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_slow_ema_var = tk.StringVar(value="21")
        ttk.Entry(self.ema_params_frame,
                  textvariable=self.backtest_slow_ema_var).grid(
            row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        ttk.Label(self.ema_params_frame, text="Signal EMA:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backtest_signal_ema_var = tk.StringVar(value="5")
        ttk.Entry(
            self.ema_params_frame, textvariable=self.backtest_signal_ema_var
        ).grid(row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Toon juiste parameters frame o.b.v. geselecteerde strategie
        self.update_backtest_parameters_frame()

        # Opties
        options_frame = ttk.LabelFrame(self.backtest_tab, text="Opties")
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        self.backtest_plot_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Plot resultaten",
            variable=self.backtest_plot_var
        ).pack(side=tk.LEFT, padx=5, pady=5)

        # Output frame
        output_frame = ttk.LabelFrame(self.backtest_tab, text="Uitvoer")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Output textbox met scrollbar
        scrollbar = ttk.Scrollbar(output_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.backtest_output = tk.Text(
            output_frame,
            height=10,
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            bg="#f0f0f0",
        )
        self.backtest_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.backtest_output.yview)

        # Buttons
        button_frame = ttk.Frame(self.backtest_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Start Backtest",
                   command=self.run_backtest).pack(
            side=tk.RIGHT, padx=5
        )

        ttk.Button(
            button_frame,
            text="Open Resultaten Map",
            command=lambda: self.open_folder("backtest_results"),
        ).pack(side=tk.RIGHT, padx=5)

    def setup_optimize_tab(self):
        """Stel het optimalisatie tabblad in."""
        # Main frame
        main_frame = ttk.Frame(self.optimize_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Input frame links
        input_frame = ttk.LabelFrame(main_frame,
                                     text="Optimalisatie Parameters")
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5,
                         pady=5)

        # Strategie selectie
        ttk.Label(input_frame, text="Strategie:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_strategy_var = tk.StringVar(value="turtle")
        strategy_combobox = ttk.Combobox(
            input_frame,
            textvariable=self.optimize_strategy_var,
            values=["turtle", "ema"],
            state="readonly",
        )
        strategy_combobox.grid(row=0, column=1, sticky=tk.W + tk.E, padx=5,
                               pady=5)
        strategy_combobox.bind("<<ComboboxSelected>>",
                               self.on_optimize_strategy_change)

        # Symbolen
        ttk.Label(input_frame, text="Symbolen:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        symbols = self.config.get("symbols", ["EURUSD", "USDJPY"])
        self.optimize_symbols_var = tk.StringVar(value=", ".join(symbols))
        ttk.Entry(input_frame, textvariable=self.optimize_symbols_var).grid(
            row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Timeframe
        ttk.Label(input_frame, text="Timeframe:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_timeframe_var = tk.StringVar(
            value=self.config.get("timeframe", "H4")
        )
        ttk.Combobox(
            input_frame,
            textvariable=self.optimize_timeframe_var,
            values=["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
            state="readonly",
        ).grid(row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Periode
        ttk.Label(input_frame, text="Periode:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_period_var = tk.StringVar(value="1y")
        ttk.Combobox(
            input_frame,
            textvariable=self.optimize_period_var,
            values=["1m", "3m", "6m", "1y", "2y", "5y"],
            state="readonly",
        ).grid(row=3, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Metric om te optimaliseren
        ttk.Label(input_frame, text="Optimaliseer voor:").grid(
            row=4, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_metric_var = tk.StringVar(value="sharpe")
        ttk.Combobox(
            input_frame,
            textvariable=self.optimize_metric_var,
            values=["sharpe", "return", "drawdown", "profit_factor"],
            state="readonly",
        ).grid(row=4, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Maximum combinaties
        ttk.Label(input_frame, text="Max combinaties:").grid(
            row=5, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_max_combinations_var = tk.StringVar(value="50")
        ttk.Entry(input_frame,
                  textvariable=self.optimize_max_combinations_var).grid(
            row=5, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Parameter ranges frame
        param_frame = ttk.LabelFrame(main_frame, text="Parameter Bereiken")
        param_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5,
                         pady=5)

        # Maak frames voor verschillende strategieën
        self.turtle_opt_frame = ttk.Frame(param_frame)
        self.ema_opt_frame = ttk.Frame(param_frame)

        # Turtle parameters
        ttk.Label(self.turtle_opt_frame, text="Entry Period:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_entry_range_var = tk.StringVar(value="10,20,30,40")
        ttk.Entry(
            self.turtle_opt_frame, textvariable=self.optimize_entry_range_var
        ).grid(row=0, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        ttk.Label(self.turtle_opt_frame, text="Exit Period:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_exit_range_var = tk.StringVar(value="5,10,15,20")
        ttk.Entry(
            self.turtle_opt_frame, textvariable=self.optimize_exit_range_var
        ).grid(row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        ttk.Label(self.turtle_opt_frame, text="ATR Period:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_atr_range_var = tk.StringVar(value="10,14,20")
        ttk.Entry(self.turtle_opt_frame,
                  textvariable=self.optimize_atr_range_var).grid(
            row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # EMA parameters
        ttk.Label(self.ema_opt_frame, text="Fast EMA:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_fast_ema_range_var = tk.StringVar(value="5,9,12,15")
        ttk.Entry(
            self.ema_opt_frame, textvariable=self.optimize_fast_ema_range_var
        ).grid(row=0, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        ttk.Label(self.ema_opt_frame, text="Slow EMA:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_slow_ema_range_var = tk.StringVar(value="20,25,30")
        ttk.Entry(
            self.ema_opt_frame, textvariable=self.optimize_slow_ema_range_var
        ).grid(row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        ttk.Label(self.ema_opt_frame, text="Signal EMA:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.optimize_signal_ema_range_var = tk.StringVar(value="5,7,9")
        ttk.Entry(
            self.ema_opt_frame, textvariable=self.optimize_signal_ema_range_var
        ).grid(row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Beschrijving labels
        ttk.Label(self.turtle_opt_frame, text="Komma-gescheiden waarden").grid(
            row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5
        )

        ttk.Label(self.ema_opt_frame, text="Komma-gescheiden waarden").grid(
            row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5
        )

        # Toon juiste parameters frame o.b.v. geselecteerde strategie
        self.update_optimize_parameters_frame()

        # Output frame
        output_frame = ttk.LabelFrame(self.optimize_tab, text="Uitvoer")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Output textbox met scrollbar
        scrollbar = ttk.Scrollbar(output_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.optimize_output = tk.Text(
            output_frame,
            height=10,
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            bg="#f0f0f0",
        )
        self.optimize_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.optimize_output.yview)

        # Buttons
        button_frame = ttk.Frame(self.optimize_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            button_frame, text="Start Optimalisatie",
            command=self.run_optimization
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Open Resultaten Map",
            command=lambda: self.open_folder("optimization_results"),
        ).pack(side=tk.RIGHT, padx=5)

    def setup_live_tab(self):
        """Stel het live trading tabblad in."""
        # Main frame
        main_frame = ttk.Frame(self.live_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # MT5 status frame
        status_frame = ttk.LabelFrame(main_frame, text="MetaTrader 5 Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        # Status indicators
        self.mt5_status_var = tk.StringVar(value="Niet verbonden")
        ttk.Label(status_frame, text="Status:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        ttk.Label(status_frame, textvariable=self.mt5_status_var).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5
        )

        # Verbindingsbutton
        self.connect_button = ttk.Button(
            status_frame, text="Verbinden", command=self.toggle_connection
        )
        self.connect_button.grid(row=0, column=2, padx=5, pady=5)

        # Account info indicators
        self.account_balance_var = tk.StringVar(value="- €")
        ttk.Label(status_frame, text="Balans:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        ttk.Label(status_frame, textvariable=self.account_balance_var).grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=5
        )

        self.account_equity_var = tk.StringVar(value="- €")
        ttk.Label(status_frame, text="Equity:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        ttk.Label(status_frame, textvariable=self.account_equity_var).grid(
            row=2, column=1, sticky=tk.W, padx=5, pady=5
        )

        # Strategie selectie frame
        strategy_frame = ttk.LabelFrame(main_frame, text="Trading Strategie")
        strategy_frame.pack(fill=tk.X, padx=5, pady=5)

        # Strategie selectie
        ttk.Label(strategy_frame, text="Actieve strategie:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.live_strategy_var = tk.StringVar(value="turtle")
        ttk.Combobox(
            strategy_frame,
            textvariable=self.live_strategy_var,
            values=["turtle", "ema"],
            state="readonly",
        ).grid(row=0, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Symbolen
        ttk.Label(strategy_frame, text="Symbolen:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        symbols = self.config.get("symbols", ["EURUSD", "USDJPY"])
        self.live_symbols_var = tk.StringVar(value=", ".join(symbols))
        ttk.Entry(strategy_frame, textvariable=self.live_symbols_var).grid(
            row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Timeframe
        ttk.Label(strategy_frame, text="Timeframe:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.live_timeframe_var = tk.StringVar(
            value=self.config.get("timeframe", "H4"))
        ttk.Combobox(
            strategy_frame,
            textvariable=self.live_timeframe_var,
            values=["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
            state="readonly",
        ).grid(row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Risico
        ttk.Label(strategy_frame, text="Risico per trade:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=5
        )
        risk_frame = ttk.Frame(strategy_frame)
        risk_frame.grid(row=3, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        self.live_risk_var = tk.StringVar(value="1")
        ttk.Entry(risk_frame, textvariable=self.live_risk_var, width=5).pack(
            side=tk.LEFT
        )
        ttk.Label(risk_frame, text="%").pack(side=tk.LEFT)

        # Interval
        ttk.Label(strategy_frame, text="Check interval:").grid(
            row=4, column=0, sticky=tk.W, padx=5, pady=5
        )
        interval_frame = ttk.Frame(strategy_frame)
        interval_frame.grid(row=4, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        self.live_interval_var = tk.StringVar(value="300")
        ttk.Entry(interval_frame, textvariable=self.live_interval_var,
                  width=5).pack(
            side=tk.LEFT
        )
        ttk.Label(interval_frame, text="seconden").pack(side=tk.LEFT)

        # Open posities frame
        positions_frame = ttk.LabelFrame(main_frame, text="Open Posities")
        positions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview voor posities
        self.positions_tree = ttk.Treeview(
            positions_frame,
            columns=(
            "symbol", "direction", "size", "entry", "current", "profit"),
            show="headings",
            height=5,
        )

        # Definieer kolommen
        self.positions_tree.heading("symbol", text="Symbool")
        self.positions_tree.heading("direction", text="Richting")
        self.positions_tree.heading("size", text="Grootte")
        self.positions_tree.heading("entry", text="Entry")
        self.positions_tree.heading("current", text="Huidig")
        self.positions_tree.heading("profit", text="Winst/Verlies")

        # Kolom breedtes
        self.positions_tree.column("symbol", width=80)
        self.positions_tree.column("direction", width=80)
        self.positions_tree.column("size", width=80)
        self.positions_tree.column("entry", width=80)
        self.positions_tree.column("current", width=80)
        self.positions_tree.column("profit", width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            positions_frame, orient="vertical",
            command=self.positions_tree.yview
        )
        self.positions_tree.configure(yscrollcommand=scrollbar.set)

        # Layout
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.positions_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Trading Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Log textbox met scrollbar
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.live_log = tk.Text(
            log_frame,
            height=10,
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            bg="#f0f0f0",
        )
        self.live_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.live_log.yview)

        # Buttons
        button_frame = ttk.Frame(self.live_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.start_button = ttk.Button(
            button_frame, text="Start Trading", command=self.start_trading
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            button_frame,
            text="Stop Trading",
            command=self.stop_trading,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame, text="Sluit Alle Posities",
            command=self.close_all_positions
        ).pack(side=tk.RIGHT, padx=5)

    def setup_config_tab(self):
        """Stel het configuratie tabblad in."""
        # Main frame
        main_frame = ttk.Frame(self.config_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # MT5 configuratie
        mt5_frame = ttk.LabelFrame(main_frame, text="MetaTrader 5 Configuratie")
        mt5_frame.pack(fill=tk.X, padx=5, pady=5)

        # MT5 pad
        ttk.Label(mt5_frame, text="MT5 pad:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.mt5_path_var = tk.StringVar(
            value=self.config.get("mt5", {}).get(
                "mt5_path", "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
            )
        )
        path_frame = ttk.Frame(mt5_frame)
        path_frame.grid(row=0, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        ttk.Entry(path_frame, textvariable=self.mt5_path_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(path_frame, text="Bladeren",
                   command=self.browse_mt5_path).pack(
            side=tk.RIGHT
        )

        # MT5 login
        ttk.Label(mt5_frame, text="Login:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.mt5_login_var = tk.StringVar(
            value=str(self.config.get("mt5", {}).get("login", ""))
        )
        ttk.Entry(mt5_frame, textvariable=self.mt5_login_var).grid(
            row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # MT5 wachtwoord
        ttk.Label(mt5_frame, text="Wachtwoord:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.mt5_password_var = tk.StringVar(
            value=self.config.get("mt5", {}).get("password", "")
        )
        ttk.Entry(mt5_frame, textvariable=self.mt5_password_var, show="*").grid(
            row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # MT5 server
        ttk.Label(mt5_frame, text="Server:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.mt5_server_var = tk.StringVar(
            value=self.config.get("mt5", {}).get("server", "")
        )
        ttk.Entry(mt5_frame, textvariable=self.mt5_server_var).grid(
            row=3, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Risico configuratie
        risk_frame = ttk.LabelFrame(main_frame, text="Risico Configuratie")
        risk_frame.pack(fill=tk.X, padx=5, pady=5)

        # Risico per trade
        ttk.Label(risk_frame, text="Risico per trade (%):").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.risk_per_trade_var = tk.StringVar(
            value=str(
                self.config.get("risk", {}).get("risk_per_trade", 0.01) * 100)
        )
        ttk.Entry(risk_frame, textvariable=self.risk_per_trade_var).grid(
            row=0, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Max dagelijks verlies
        ttk.Label(risk_frame, text="Max dagelijks verlies (%):").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.max_daily_loss_var = tk.StringVar(
            value=str(
                self.config.get("risk", {}).get("max_daily_loss", 0.05) * 100)
        )
        ttk.Entry(risk_frame, textvariable=self.max_daily_loss_var).grid(
            row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Max posities
        ttk.Label(risk_frame, text="Max aantal posities:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.max_positions_var = tk.StringVar(
            value=str(self.config.get("risk", {}).get("max_positions", 5))
        )
        ttk.Entry(risk_frame, textvariable=self.max_positions_var).grid(
            row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Max gecorreleerde posities
        ttk.Label(risk_frame, text="Max gecorreleerde posities:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.max_correlated_var = tk.StringVar(
            value=str(self.config.get("risk", {}).get("max_correlated", 2))
        )
        ttk.Entry(risk_frame, textvariable=self.max_correlated_var).grid(
            row=3, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Algemene configuratie
        general_frame = ttk.LabelFrame(main_frame, text="Algemene Configuratie")
        general_frame.pack(fill=tk.X, padx=5, pady=5)

        # Symbolen
        ttk.Label(general_frame, text="Symbolen:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.symbols_var = tk.StringVar(
            value=", ".join(self.config.get("symbols", ["EURUSD", "USDJPY"]))
        )
        ttk.Entry(general_frame, textvariable=self.symbols_var).grid(
            row=0, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Timeframe
        ttk.Label(general_frame, text="Timeframe:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.timeframe_var = tk.StringVar(
            value=self.config.get("timeframe", "H4"))
        ttk.Combobox(
            general_frame,
            textvariable=self.timeframe_var,
            values=["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
            state="readonly",
        ).grid(row=1, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

        # Interval
        ttk.Label(general_frame, text="Check interval (s):").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.interval_var = tk.StringVar(
            value=str(self.config.get("interval", 300)))
        ttk.Entry(general_frame, textvariable=self.interval_var).grid(
            row=2, column=1, sticky=tk.W + tk.E, padx=5, pady=5
        )

        # Buttons
        button_frame = ttk.Frame(self.config_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Opslaan",
                   command=self.save_configuration).pack(
            side=tk.RIGHT, padx=5
        )

        ttk.Button(
            button_frame, text="Herstellen", command=self.reset_configuration
        ).pack(side=tk.RIGHT, padx=5)

    # Event handlers
    def on_backtest_strategy_change(self, event):
        """Handler voor wijzigen strategie in backtest tab."""
        self.update_backtest_parameters_frame()

    def on_optimize_strategy_change(self, event):
        """Handler voor wijzigen strategie in optimalisatie tab."""
        self.update_optimize_parameters_frame()

    def update_backtest_parameters_frame(self):
        """Update parameters frame op basis van geselecteerde strategie in backtest tab."""
        strategy = self.backtest_strategy_var.get()

        # Verwijder huidige parameters frame
        self.turtle_params_frame.pack_forget()
        self.ema_params_frame.pack_forget()

        # Toon juiste parameters frame
        if strategy == "turtle":
            self.turtle_params_frame.pack(fill=tk.BOTH, expand=True, padx=5,
                                          pady=5)
        elif strategy == "ema":
            self.ema_params_frame.pack(fill=tk.BOTH, expand=True, padx=5,
                                       pady=5)

    def update_optimize_parameters_frame(self):
        """Update parameters frame op basis van geselecteerde strategie in optimalisatie tab."""
        strategy = self.optimize_strategy_var.get()

        # Verwijder huidige parameters frame
        self.turtle_opt_frame.pack_forget()
        self.ema_opt_frame.pack_forget()

        # Toon juiste parameters frame
        if strategy == "turtle":
            self.turtle_opt_frame.pack(fill=tk.BOTH, expand=True, padx=5,
                                       pady=5)
        elif strategy == "ema":
            self.ema_opt_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def browse_mt5_path(self):
        """Open file browser voor MT5 executable."""
        filename = filedialog.askopenfilename(
            title="Selecteer MetaTrader 5 executable",
            filetypes=[("Executable", "*.exe")],
            initialdir="C:\\Program Files",
        )
        if filename:
            self.mt5_path_var.set(filename)

    def save_configuration(self):
        """Sla configuratie op."""
        try:
            # MT5 configuratie
            mt5_config = {
                "mt5_path": self.mt5_path_var.get(),
                "login": (
                    int(self.mt5_login_var.get()) if self.mt5_login_var.get() else 0
                ),
                "password": self.mt5_password_var.get(),
                "server": self.mt5_server_var.get(),
            }

            # Risico configuratie
            risk_config = {
                "risk_per_trade": float(self.risk_per_trade_var.get()) / 100,
                "max_daily_loss": float(self.max_daily_loss_var.get()) / 100,
                "max_positions": int(self.max_positions_var.get()),
                "max_correlated": int(self.max_correlated_var.get()),
            }

            # Symbolen
            symbols = [
                s.strip() for s in self.symbols_var.get().split(",") if
                s.strip()
            ]

            # Volledige configuratie
            config = {
                "mt5": mt5_config,
                "risk": risk_config,
                "symbols": symbols,
                "timeframe": self.timeframe_var.get(),
                "interval": int(self.interval_var.get()),
            }

            # Sla op
            self.save_config(config)
            self.config = config
            messagebox.showinfo("Configuratie",
                                "Configuratie succesvol opgeslagen")

        except Exception as e:
            messagebox.showerror("Configuratie opslaan",
                                 f"Fout bij opslaan: {e}")

    def reset_configuration(self):
        """Herstellen configuratie naar opgeslagen waarden."""
        config = self.load_config()
        self.config = config

        # Update UI velden
        # MT5
        self.mt5_path_var.set(
            config.get("mt5", {}).get(
                "mt5_path", "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
            )
        )
        self.mt5_login_var.set(str(config.get("mt5", {}).get("login", "")))
        self.mt5_password_var.set(config.get("mt5", {}).get("password", ""))
        self.mt5_server_var.set(config.get("mt5", {}).get("server", ""))

        # Risico
        self.risk_per_trade_var.set(
            str(config.get("risk", {}).get("risk_per_trade", 0.01) * 100)
        )
        self.max_daily_loss_var.set(
            str(config.get("risk", {}).get("max_daily_loss", 0.05) * 100)
        )
        self.max_positions_var.set(
            str(config.get("risk", {}).get("max_positions", 5)))
        self.max_correlated_var.set(
            str(config.get("risk", {}).get("max_correlated", 2))
        )

        # Algemeen
        self.symbols_var.set(
            ", ".join(config.get("symbols", ["EURUSD", "USDJPY"])))
        self.timeframe_var.set(config.get("timeframe", "H4"))
        self.interval_var.set(str(config.get("interval", 300)))

        self.show_status("Configuratie hersteld")

    def toggle_connection(self):
        """Toggle MT5 verbinding."""
        # ToDo: Implementeer MT5 verbinding logica
        if self.mt5_status_var.get() == "Niet verbonden":
            self.mt5_status_var.set("Verbonden")
            self.connect_button.configure(text="Verbreken")
            self.account_balance_var.set("10,000.00 €")
            self.account_equity_var.set("10,000.00 €")
        else:
            self.mt5_status_var.set("Niet verbonden")
            self.connect_button.configure(text="Verbinden")
            self.account_balance_var.set("- €")
            self.account_equity_var.set("- €")

    def start_trading(self):
        """Start live trading."""
        # ToDo: Implementeer live trading start logica
        self.live_log.insert(
            tk.END,
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
            f"- Trading gestart met {self.live_strategy_var.get()} strategie\n",
        )
        self.live_log.see(tk.END)

        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)

    def stop_trading(self):
        """Stop live trading."""
        # ToDo: Implementeer live trading stop logica
        self.live_log.insert(
            tk.END,
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} " f"- Trading gestopt\n",
        )
        self.live_log.see(tk.END)

        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    def close_all_positions(self):
        """Sluit alle open posities."""
        # ToDo: Implementeer posities sluiten logica
        confirm = messagebox.askyesno(
            "Posities sluiten",
            "Weet je zeker dat je alle open posities wilt sluiten?"
        )
        if confirm:
            # Simulatie voor ui demo
            self.positions_tree.delete(*self.positions_tree.get_children())

            self.live_log.insert(
                tk.END,
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                f"- Alle posities gesloten\n",
            )
            self.live_log.see(tk.END)

    def run_backtest(self):
        """Voer backtest uit met de ingestelde parameters."""
        # Backtest parameters verzamelen
        strategy = self.backtest_strategy_var.get()
        symbols = [
            s.strip() for s in self.backtest_symbols_var.get().split(",") if
            s.strip()
        ]
        timeframe = self.backtest_timeframe_var.get()
        period = self.backtest_period_var.get()
        initial_cash = self.backtest_cash_var.get()

        # Strategie specifieke parameters
        if strategy == "turtle":
            strategy_params = {
                "entry_period": self.backtest_entry_period_var.get(),
                "exit_period": self.backtest_exit_period_var.get(),
                "atr_period": self.backtest_atr_period_var.get(),
            }
        else:  # EMA
            strategy_params = {
                "fast_ema": self.backtest_fast_ema_var.get(),
                "slow_ema": self.backtest_slow_ema_var.get(),
                "signal_ema": self.backtest_signal_ema_var.get(),
            }

        # Opties
        plot = self.backtest_plot_var.get()

        # Commando opbouwen
        cmd = [
            sys.executable,
            "-m",
            "src.analysis.backtest",
            "--strategy",
            strategy,
            "--timeframe",
            timeframe,
            "--period",
            period,
            "--initial-cash",
            initial_cash,
            "--symbols",
        ]

        # Symbolen toevoegen
        cmd.extend(symbols)

        # Strategie parameters toevoegen
        if strategy == "turtle":
            cmd.extend(
                [
                    "--entry-period",
                    strategy_params["entry_period"],
                    "--exit-period",
                    strategy_params["exit_period"],
                    "--atr-period",
                    strategy_params["atr_period"],
                ]
            )
        else:  # EMA
            cmd.extend(
                [
                    "--fast-ema",
                    strategy_params["fast_ema"],
                    "--slow-ema",
                    strategy_params["slow_ema"],
                    "--signal-ema",
                    strategy_params["signal_ema"],
                ]
            )

        # Plot optie
        if plot:
            cmd.append("--plot")

        # Log commando
        self.backtest_output.delete(1.0, tk.END)
        self.backtest_output.insert(tk.END, f"Uitvoeren: {' '.join(cmd)}\n\n")
        self.show_status("Backtest wordt uitgevoerd...")

        # Uitvoeren in aparte thread
        threading.Thread(
            target=self._run_process, args=(cmd, self.backtest_output)
        ).start()

    def run_optimization(self):
        """Voer optimalisatie uit met de ingestelde parameters."""
        # Optimalisatie parameters verzamelen
        strategy = self.optimize_strategy_var.get()
        symbols = [
            s.strip() for s in self.optimize_symbols_var.get().split(",") if
            s.strip()
        ]
        timeframe = self.optimize_timeframe_var.get()
        period = self.optimize_period_var.get()
        metric = self.optimize_metric_var.get()
        max_combinations = self.optimize_max_combinations_var.get()

        # Parameter ranges
        if strategy == "turtle":
            param_ranges = {
                "entry_period_range": self.optimize_entry_range_var.get(),
                "exit_period_range": self.optimize_exit_range_var.get(),
                "atr_period_range": self.optimize_atr_range_var.get(),
            }
        else:  # EMA
            param_ranges = {
                "fast_ema_range": self.optimize_fast_ema_range_var.get(),
                "slow_ema_range": self.optimize_slow_ema_range_var.get(),
                "signal_ema_range": self.optimize_signal_ema_range_var.get(),
            }

        # Commando opbouwen
        cmd = [
            sys.executable,
            "-m",
            "src.analysis.optimizer",
            "--strategy",
            strategy,
            "--timeframe",
            timeframe,
            "--period",
            period,
            "--metric",
            metric,
            "--max-combinations",
            max_combinations,
            "--symbols",
        ]

        # Symbolen toevoegen
        cmd.extend(symbols)

        # Parameter ranges toevoegen
        if strategy == "turtle":
            cmd.extend(
                [
                    "--entry-period-range",
                    param_ranges["entry_period_range"],
                    "--exit-period-range",
                    param_ranges["exit_period_range"],
                    "--atr-period-range",
                    param_ranges["atr_period_range"],
                ]
            )
        else:  # EMA
            cmd.extend(
                [
                    "--fast-ema-range",
                    param_ranges["fast_ema_range"],
                    "--slow-ema-range",
                    param_ranges["slow_ema_range"],
                    "--signal-ema-range",
                    param_ranges["signal_ema_range"],
                ]
            )

        # Log commando
        self.optimize_output.delete(1.0, tk.END)
        self.optimize_output.insert(tk.END, f"Uitvoeren: {' '.join(cmd)}\n\n")
        self.show_status("Optimalisatie wordt uitgevoerd...")

        # Uitvoeren in aparte thread
        threading.Thread(
            target=self._run_process, args=(cmd, self.optimize_output)
        ).start()

    def _run_process(self, cmd, output_widget):
        """
        Draai een proces en schrijf uitvoer naar widget.

        Args:
            cmd: Command lijst om uit te voeren
            output_widget: Tk widget om uitvoer naar te schrijven
        """
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # Lees uitvoer regel voor regel
            for line in process.stdout:
                self.root.after(
                    0, lambda l=line: self._append_to_output(output_widget, l)
                )

            process.wait()

            if process.returncode == 0:
                self.root.after(
                    0, lambda: self.show_status("Proces succesvol voltooid")
                )
            else:
                self.root.after(
                    0,
                    lambda: self.show_status(
                        f"Proces voltooid met foutcode {process.returncode}"
                    ),
                )

        except Exception as e:
            self.root.after(
                0,
                lambda: self._append_to_output(
                    output_widget, f"\nFout bij uitvoeren: {e}\n"
                ),
            )
            self.root.after(0, lambda: self.show_status(
                "Fout bij uitvoeren proces"))

    def _append_to_output(self, widget, text):
        """
        Voeg tekst toe aan output widget.

        Args:
            widget: Tk widget om tekst aan toe te voegen
            text: Toe te voegen tekst
        """
        widget.insert(tk.END, text)
        widget.see(tk.END)

    def open_folder(self, folder_name):
        """
        Open een map in de explorer.

        Args:
            folder_name: Naam van de map onder project root
        """
        folder_path = os.path.join(project_root, folder_name)

        # Controleer of map bestaat, maak aan indien nodig
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except Exception as e:
                messagebox.showerror("Map openen",
                                     f"Kon map niet aanmaken: {e}")
                return

        # Open map
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", folder_path])
            else:  # Linux
                subprocess.call(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Map openen", f"Kon map niet openen: {e}")

    def show_status(self, message):
        """
        Toon een bericht in de statusbalk.

        Args:
            message: Bericht om te tonen
        """
        self.status_var.set(message)
        # Reset na 5 seconden
        self.root.after(5000, lambda: self.status_var.set("Gereed"))


def main():
    """Hoofdfunctie voor het dashboard."""
    root = tk.Tk()
    app = SophiaDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
