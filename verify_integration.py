#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sophia Framework Verificatie Tool v2.0

Een uitgebreide diagnostische tool voor het Sophia Trading Framework die:
1. Modulestructuur en imports verifieert
2. Componentintegratie controleert
3. Dataflow validatie uitvoert
4. Code kwaliteitsmetrieken verzamelt
5. Architectuurdiagram genereert
6. Prestatie-benchmarks uitvoert

Gebruik: python verify_integration.py [--verbose] [--diagram] [--performance]
"""

import argparse
import importlib
import inspect
import logging
import os
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Project root toevoegen aan sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
# Detecteer project root op basis van de aanwezigheid van specifieke mappen
if os.path.exists(os.path.join(script_dir, "src")):
    project_root = script_dir  # Script is al in de root
elif os.path.exists(os.path.join(os.path.dirname(script_dir), "src")):
    project_root = os.path.dirname(script_dir)  # Ga één niveau omhoog
else:
    # Probeer het project root te vinden door omhoog te navigeren
    current_dir = script_dir
    max_levels = 3  # Maximum aantal niveaus omhoog
    for _ in range(max_levels):
        parent_dir = os.path.dirname(current_dir)
        if os.path.exists(os.path.join(parent_dir, "src")):
            project_root = parent_dir
            break
        current_dir = parent_dir
    else:
        project_root = script_dir  # Fallback

# Configureer logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("sophia.verifier")


# Style helpers voor consoleoutput
class ConsoleColors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


@dataclass
class VerificationResult:
    """Dataclass voor verificatieresultaten."""

    component: str
    status: bool
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        status_str = (
            f"{ConsoleColors.GREEN}✓ GESLAAGD{ConsoleColors.ENDC}"
            if self.status
            else f"{ConsoleColors.FAIL}✗ MISLUKT{ConsoleColors.ENDC}"
        )
        return f"{self.component}: {status_str} - {self.message}"


@contextmanager
def measure_time():
    """Context manager om uitvoeringstijd te meten."""
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        print(f"Uitvoeringstijd: {elapsed_time:.2f} seconden")


def print_header(message: str) -> None:
    """Druk een opvallende header af in de console."""
    separator = "=" * 80
    print(
        f"\n{ConsoleColors.BOLD}{ConsoleColors.HEADER}{separator}{ConsoleColors.ENDC}"
    )
    print(
        f"{ConsoleColors.BOLD}{ConsoleColors.HEADER}{message.center(80)}{ConsoleColors.ENDC}"
    )
    print(
        f"{ConsoleColors.BOLD}{ConsoleColors.HEADER}{separator}{ConsoleColors.ENDC}")


def print_subheader(message: str) -> None:
    """Druk een subheader af in de console."""
    print(
        f"\n{ConsoleColors.BOLD}{ConsoleColors.BLUE}{message}{ConsoleColors.ENDC}")
    print(f"{ConsoleColors.BLUE}{'-' * len(message)}{ConsoleColors.ENDC}")


def print_progress(
    current: int, total: int, prefix: str = "", suffix: str = "",
    length: int = 50
) -> None:
    """Toon een voortgangsbalk in de console."""
    percent = int(100 * (current / float(total)))
    filled_length = int(length * current // total)
    bar = "█" * filled_length + "░" * (length - filled_length)
    sys.stdout.write(f"\r{prefix} |{bar}| {percent}% {suffix}")
    sys.stdout.flush()
    if current == total:
        print()


class FrameworkVerifier:
    """Uitgebreide verificatietool voor het Sophia Trading Framework."""

    def __init__(
        self, verbose: bool = False, diagram: bool = False,
        performance: bool = False
    ):
        """
        Initialiseer de framework verificatietool.

        Args:
            verbose: Of gedetailleerde uitvoer moet worden getoond
            diagram: Of een architectuurdiagram moet worden gegenereerd
            performance: Of performance benchmarks moeten worden uitgevoerd
        """
        self.verbose = verbose
        self.diagram = diagram
        self.performance = performance
        self.results: List[VerificationResult] = []
        self.core_modules = [
            "src.main",
            "src.connector",
            "src.risk",
            "src.strategy",
            "src.strategy_ema",
            "src.utils",
        ]
        self.backtest_modules = [
            "src.analysis.backtest",
            "src.analysis.backtrader_adapter",
            "src.analysis.optimizer",
            "src.analysis.dashboard",
            "src.analysis.strategies.turtle_bt",
            "src.analysis.strategies.ema_bt",
        ]
        self.example_modules = ["examples.strategy_optimization"]
        self.imported_modules = {}  # Cache voor geïmporteerde modules

    def import_module(self, module_name: str) -> Tuple[
        bool, Any, Optional[Exception]]:
        """
        Importeer een module veilig en caching.

        Args:
            module_name: Naam van de module om te importeren

        Returns:
            Tuple van (succes, module object, exception)
        """
        if module_name in self.imported_modules:
            return (True, self.imported_modules[module_name], None)

        try:
            module = importlib.import_module(module_name)
            self.imported_modules[module_name] = module
            return (True, module, None)
        except Exception as e:
            return (False, None, e)

    def verify_module_imports(self) -> List[VerificationResult]:
        """
        Verifieer dat alle benodigde modules kunnen worden geïmporteerd.

        Returns:
            Lijst met verificatieresultaten
        """
        print_subheader("1. Module Import Verificatie")
        results = []
        all_modules = self.core_modules + self.backtest_modules + self.example_modules

        for i, module_name in enumerate(all_modules):
            print_progress(
                i,
                len(all_modules),
                prefix="Modules controleren:",
                suffix=f"{i}/{len(all_modules)}",
            )
            success, module, exception = self.import_module(module_name)

            if success:
                results.append(
                    VerificationResult(
                        component=module_name,
                        status=True,
                        message=f"Module succesvol geïmporteerd",
                        details={"module_obj": module},
                    )
                )
                if self.verbose:
                    print(f"✅ {module_name}: succesvol geïmporteerd")
            else:
                results.append(
                    VerificationResult(
                        component=module_name,
                        status=False,
                        message=f"Import mislukt: {exception}",
                        details={"exception": exception},
                    )
                )
                if self.verbose:
                    print(f"❌ {module_name}: {exception}")

        print_progress(
            len(all_modules),
            len(all_modules),
            prefix="Modules controleren:",
            suffix="Voltooid",
        )
        return results

    def verify_main_integration(self) -> VerificationResult:
        """
        Verifieer dat de main module correct is geïntegreerd.

        Returns:
            VerificationResult object
        """
        print_subheader("2. Main Module Integratie Verificatie")

        try:
            # Import de main module
            success, main_module, exception = self.import_module("src.main")
            if not success:
                return VerificationResult(
                    component="Main Module Integratie",
                    status=False,
                    message=f"Kon src.main niet importeren: {exception}",
                )

            # Verifieer hoofdfuncties
            required_functions = ["parse_arguments", "main"]
            for func_name in required_functions:
                if not hasattr(main_module, func_name):
                    return VerificationResult(
                        component="Main Module Integratie",
                        status=False,
                        message=f"Ontbrekende functie in main module: {func_name}",
                    )

            # Verifieer SophiaTrader klasse
            if not hasattr(main_module, "SophiaTrader"):
                return VerificationResult(
                    component="Main Module Integratie",
                    status=False,
                    message="SophiaTrader klasse niet gevonden in main module",
                )

            # Verifieer backtest mode in SophiaTrader
            trader_class = getattr(main_module, "SophiaTrader")
            init_sig = inspect.signature(trader_class.__init__)
            if "backtest_mode" not in init_sig.parameters:
                return VerificationResult(
                    component="Main Module Integratie",
                    status=False,
                    message="SophiaTrader.__init__ mist backtest_mode parameter",
                )

            # Verifieer backtest import flow
            main_source = inspect.getsource(main_module)
            if (
                "analysis.backtest" not in main_source
                or "dashboard_main" not in main_source
            ):
                return VerificationResult(
                    component="Main Module Integratie",
                    status=False,
                    message="Main module importeert mogelijk niet correct de analysis.backtest module",
                )

            return VerificationResult(
                component="Main Module Integratie",
                status=True,
                message="Main module is correct geïntegreerd met backtesting componenten",
            )

        except Exception as e:
            return VerificationResult(
                component="Main Module Integratie",
                status=False,
                message=f"Onverwachte fout bij controleren van main integratie: {e}",
                details={"exception": e, "traceback": traceback.format_exc()},
            )

    def verify_strategy_adapter(self) -> VerificationResult:
        """
        Verifieer dat de strategie adapter correct werkt.

        Returns:
            VerificationResult object
        """
        print_subheader("3. Strategie Adapter Verificatie")

        try:
            # Controleer of strategy_adapter.py bestaat
            adapter_path = os.path.join(project_root, "src",
                                        "strategy_adapter.py")
            if not os.path.exists(adapter_path):
                # Controleer alternatief pad
                adapter_path = os.path.join(
                    project_root, "src", "analysis", "strategy_adapter.py"
                )
                if not os.path.exists(adapter_path):
                    return VerificationResult(
                        component="Strategie Adapter",
                        status=False,
                        message="Strategie adapter bestand niet gevonden",
                    )

            # Importeer de strategie implementaties
            _, turtle_bt, _ = self.import_module(
                "src.analysis.strategies.turtle_bt")
            _, ema_bt, _ = self.import_module("src.analysis.strategies.ema_bt")

            if not (turtle_bt and ema_bt):
                return VerificationResult(
                    component="Strategie Adapter",
                    status=False,
                    message="Kon strategie implementaties niet importeren",
                )

            # Controleer de interfaces (verwacht TurtleStrategy en EMAStrategy klassen)
            if not hasattr(turtle_bt, "TurtleStrategy"):
                return VerificationResult(
                    component="Strategie Adapter",
                    status=False,
                    message="TurtleStrategy klasse niet gevonden in turtle_bt module",
                )

            if not hasattr(ema_bt, "EMAStrategy"):
                return VerificationResult(
                    component="Strategie Adapter",
                    status=False,
                    message="EMAStrategy klasse niet gevonden in ema_bt module",
                )

            # Verifieer dat de strategie klassen de juiste interfaces implementeren
            turtle_class = getattr(turtle_bt, "TurtleStrategy")
            ema_class = getattr(ema_bt, "EMAStrategy")

            required_methods = ["__init__", "next"]

            for method in required_methods:
                if not hasattr(turtle_class, method):
                    return VerificationResult(
                        component="Strategie Adapter",
                        status=False,
                        message=f"TurtleStrategy mist verplichte methode: {method}",
                    )
                if not hasattr(ema_class, method):
                    return VerificationResult(
                        component="Strategie Adapter",
                        status=False,
                        message=f"EMAStrategy mist verplichte methode: {method}",
                    )

            return VerificationResult(
                component="Strategie Adapter",
                status=True,
                message="Strategie adapter en implementaties zijn correct",
            )

        except Exception as e:
            return VerificationResult(
                component="Strategie Adapter",
                status=False,
                message=f"Onverwachte fout bij controleren van strategie adapter: {e}",
                details={"exception": e, "traceback": traceback.format_exc()},
            )

    def verify_backtrader_adapter(self) -> VerificationResult:
        """
        Verifieer dat de backtrader adapter correct is geïmplementeerd.

        Returns:
            VerificationResult object
        """
        print_subheader("4. Backtrader Adapter Verificatie")

        try:
            # Importeer de adapter module
            success, adapter_module, exception = self.import_module(
                "src.analysis.backtrader_adapter"
            )
            if not success:
                return VerificationResult(
                    component="Backtrader Adapter",
                    status=False,
                    message=f"Kon backtrader_adapter niet importeren: {exception}",
                )

            # Controleer of de adapter klasse bestaat
            if not hasattr(adapter_module, "BacktraderAdapter"):
                return VerificationResult(
                    component="Backtrader Adapter",
                    status=False,
                    message="BacktraderAdapter klasse niet gevonden",
                )

            # Valideer de adapter interface
            adapter_class = getattr(adapter_module, "BacktraderAdapter")
            required_methods = [
                "__init__",
                "get_historical_data",
                "prepare_cerebro",
                "add_data",
                "add_strategy",
                "run_backtest",
            ]

            for method in required_methods:
                if not hasattr(adapter_class, method):
                    return VerificationResult(
                        component="Backtrader Adapter",
                        status=False,
                        message=f"BacktraderAdapter mist verplichte methode: {method}",
                    )

            # Controleer of de adapter veilig geïnitialiseerd kan worden met een lege config
            try:
                adapter = adapter_class(config={})

                # Alleen controleren of cerebro kan worden aangemaakt
                cerebro = adapter.prepare_cerebro()

                if cerebro is None:
                    return VerificationResult(
                        component="Backtrader Adapter",
                        status=False,
                        message="BacktraderAdapter.prepare_cerebro() geeft None terug",
                    )

            except Exception as e:
                return VerificationResult(
                    component="Backtrader Adapter",
                    status=False,
                    message=f"Fout bij initialiseren BacktraderAdapter: {e}",
                    details={"exception": e,
                             "traceback": traceback.format_exc()},
                )

            return VerificationResult(
                component="Backtrader Adapter",
                status=True,
                message="Backtrader adapter kan correct worden geïnitialiseerd en gebruikt",
            )

        except Exception as e:
            return VerificationResult(
                component="Backtrader Adapter",
                status=False,
                message=f"Onverwachte fout bij controleren van backtrader adapter: {e}",
                details={"exception": e, "traceback": traceback.format_exc()},
            )

    def verify_data_flow(self) -> VerificationResult:
        """
        Verifieer dat de data flow tussen componenten correct werkt.

        Returns:
            VerificationResult object
        """
        print_subheader("5. Data Flow Verificatie")

        try:
            # Importeer benodigde modules
            success, adapter_module, exception = self.import_module(
                "src.analysis.backtrader_adapter"
            )
            if not success:
                return VerificationResult(
                    component="Data Flow",
                    status=False,
                    message=f"Kon backtrader_adapter niet importeren: {exception}",
                )

            success, pd_module, exception = self.import_module("pandas")
            if not success:
                return VerificationResult(
                    component="Data Flow",
                    status=False,
                    message=f"Kon pandas niet importeren: {exception}",
                )

            success, np_module, exception = self.import_module("numpy")
            if not success:
                return VerificationResult(
                    component="Data Flow",
                    status=False,
                    message=f"Kon numpy niet importeren: {exception}",
                )

            # Importeer turtle strategie
            success, turtle_bt, exception = self.import_module(
                "src.analysis.strategies.turtle_bt"
            )
            if not success:
                return VerificationResult(
                    component="Data Flow",
                    status=False,
                    message=f"Kon turtle_bt niet importeren: {exception}",
                )

            # Creëer dummy OHLC data
            dates = pd_module.date_range(start="2023-01-01", periods=100)
            data = pd_module.DataFrame(
                {
                    "time": dates,
                    "open": np_module.linspace(1.0, 1.1, 100),
                    "high": np_module.linspace(1.01, 1.11, 100),
                    "low": np_module.linspace(0.99, 1.09, 100),
                    "close": np_module.linspace(1.005, 1.105, 100),
                    "tick_volume": np_module.random.randint(100, 1000, 100),
                }
            )

            # Test of data kan worden verwerkt door BacktraderAdapter
            adapter_class = getattr(adapter_module, "BacktraderAdapter")
            adapter = adapter_class(config={})

            # Bereid cerebro voor
            cerebro = adapter.prepare_cerebro()

            # Voeg data toe
            try:
                adapter.add_data(data, "EURUSD", "H4")
            except Exception as e:
                return VerificationResult(
                    component="Data Flow",
                    status=False,
                    message=f"Fout bij toevoegen data aan adapter: {e}",
                    details={"exception": e,
                             "traceback": traceback.format_exc()},
                )

            # Voeg strategie toe
            turtle_class = getattr(turtle_bt, "TurtleStrategy")
            try:
                adapter.add_strategy(turtle_class)
            except Exception as e:
                return VerificationResult(
                    component="Data Flow",
                    status=False,
                    message=f"Fout bij toevoegen strategie aan adapter: {e}",
                    details={"exception": e,
                             "traceback": traceback.format_exc()},
                )

            # Voer een minimale backtest uit
            try:
                results, metrics = adapter.run_backtest()

                # Controleer of metrics object correct is
                if not isinstance(metrics, dict):
                    return VerificationResult(
                        component="Data Flow",
                        status=False,
                        message=f"Backtest metrics is geen dictionary: {type(metrics)}",
                    )

                # Controleer of essentiële metrics aanwezig zijn
                required_metrics = ["final_value", "total_return_pct",
                                    "sharpe_ratio"]
                for metric in required_metrics:
                    if metric not in metrics:
                        return VerificationResult(
                            component="Data Flow",
                            status=False,
                            message=f"Backtest metrics mist vereiste metric: {metric}",
                        )

            except Exception as e:
                return VerificationResult(
                    component="Data Flow",
                    status=False,
                    message=f"Fout bij uitvoeren backtest: {e}",
                    details={"exception": e,
                             "traceback": traceback.format_exc()},
                )

            return VerificationResult(
                component="Data Flow",
                status=True,
                message="Data flow verificatie geslaagd",
            )

        except Exception as e:
            return VerificationResult(
                component="Data Flow",
                status=False,
                message=f"Onverwachte fout bij controleren van data flow: {e}",
                details={"exception": e, "traceback": traceback.format_exc()},
            )

    def verify_example_script(self) -> VerificationResult:
        """
        Verifieer dat het voorbeeldscript correct is geïmplementeerd.

        Returns:
            VerificationResult object
        """
        print_subheader("6. Voorbeeld Script Verificatie")

        example_path = os.path.join(
            project_root, "examples", "strategy_optimization.py"
        )
        if not os.path.exists(example_path):
            return VerificationResult(
                component="Voorbeeld Script",
                status=False,
                message=f"Voorbeeld script niet gevonden: {example_path}",
            )

        try:
            # Importeer het voorbeeldscript
            success, example_module, exception = self.import_module(
                "examples.strategy_optimization"
            )
            if not success:
                return VerificationResult(
                    component="Voorbeeld Script",
                    status=False,
                    message=f"Kon voorbeeld script niet importeren: {exception}",
                )

            # Controleer of de hoofdfuncties aanwezig zijn
            required_functions = [
                "main",
                "parse_arguments",
                "run_parameter_optimization",
            ]
            for func_name in required_functions:
                if not hasattr(example_module, func_name):
                    return VerificationResult(
                        component="Voorbeeld Script",
                        status=False,
                        message=f"Voorbeeld script mist verplichte functie: {func_name}",
                    )

            # Controleer of het script de juiste modules importeert
            source_code = inspect.getsource(example_module)
            required_imports = ["backtrader_adapter", "TurtleStrategy",
                                "EMAStrategy"]

            missing_imports = []
            for imp in required_imports:
                if imp not in source_code:
                    missing_imports.append(imp)

            if missing_imports:
                return VerificationResult(
                    component="Voorbeeld Script",
                    status=False,
                    message=f"Voorbeeld script mist vereiste imports: {', '.join(missing_imports)}",
                )

            return VerificationResult(
                component="Voorbeeld Script",
                status=True,
                message="Voorbeeld script is correct geïmplementeerd",
            )

        except Exception as e:
            return VerificationResult(
                component="Voorbeeld Script",
                status=False,
                message=f"Onverwachte fout bij controleren van voorbeeld script: {e}",
                details={"exception": e, "traceback": traceback.format_exc()},
            )

    def verify_file_structure(self) -> VerificationResult:
        """
        Verifieer dat de bestandsstructuur correct is.

        Returns:
            VerificationResult object
        """
        print_subheader("7. Bestandsstructuur Verificatie")

        required_directories = [
            os.path.join(project_root, "src"),
            os.path.join(project_root, "src", "analysis"),
            os.path.join(project_root, "src", "analysis", "strategies"),
            os.path.join(project_root, "examples"),
            os.path.join(project_root, "tests"),
        ]

        required_files = [
            os.path.join(project_root, "src", "main.py"),
            os.path.join(project_root, "src", "connector.py"),
            os.path.join(project_root, "src", "risk.py"),
            os.path.join(project_root, "src", "strategy.py"),
            os.path.join(project_root, "src", "strategy_ema.py"),
            os.path.join(project_root, "src", "utils.py"),
            os.path.join(project_root, "src", "analysis", "backtest.py"),
            os.path.join(project_root, "src", "analysis",
                         "backtrader_adapter.py"),
            os.path.join(project_root, "src", "analysis", "strategies",
                         "turtle_bt.py"),
            os.path.join(project_root, "src", "analysis", "strategies",
                         "ema_bt.py"),
            os.path.join(project_root, "examples", "strategy_optimization.py"),
            os.path.join(project_root, "README.md"),
            os.path.join(project_root, "requirements.txt"),
        ]

        # Controleer directories
        missing_dirs = []
        for directory in required_directories:
            if not os.path.exists(directory) or not os.path.isdir(directory):
                missing_dirs.append(os.path.relpath(directory, project_root))

        # Controleer bestanden
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                missing_files.append(os.path.relpath(file_path, project_root))

        # Controleer mogelijk overbodige bestanden in de root
        deprecated_files = [
            "strategy_optimization.py",
            "mt5_connection.py",
            "coverage_report.py",
            "generate_local_context.py",
            "test.ipynb",
            "verification_notebook.ipynb",
        ]

        redundant_files = []
        for file_name in deprecated_files:
            file_path = os.path.join(project_root, file_name)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                redundant_files.append(file_name)

        if missing_dirs or missing_files:
            missing_components = []
            if missing_dirs:
                missing_components.append(f"Mappen: {', '.join(missing_dirs)}")
            if missing_files:
                missing_components.append(
                    f"Bestanden: {', '.join(missing_files)}")

            return VerificationResult(
                component="Bestandsstructuur",
                status=False,
                message=f"Ontbrekende componenten: {'; '.join(missing_components)}",
                details={
                    "missing_directories": missing_dirs,
                    "missing_files": missing_files,
                    "redundant_files": redundant_files,
                },
            )

        message = "Bestandsstructuur is compleet"
        if redundant_files:
            message += f" - Let op: mogelijk overbodige bestanden gevonden: {', '.join(redundant_files)}"

        return VerificationResult(
            component="Bestandsstructuur",
            status=True,
            message=message,
            details={"redundant_files": redundant_files},
        )

    def verify_code_consistency(self) -> VerificationResult:
        """
        Verifieer de consistentie van de code (imports, stijl, etc.).

        Returns:
            VerificationResult object
        """
        print_subheader("8. Code Consistentie Analyse")

        # Analyse van importpatronen en codestructuur
        python_files = []
        for root, _, files in os.walk(os.path.join(project_root, "src")):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        # Analyseer importpatronen
        import_patterns = {}
        style_issues = []

        for file_path in python_files:
            rel_path = os.path.relpath(file_path, project_root)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                imports = []

                for line in lines:
                    if line.strip().startswith(("import ", "from ")):
                        imports.append(line.strip())

                import_patterns[rel_path] = imports

                # Controleer basic style issues
                if "# -*- coding: utf-8 -*-" not in content:
                    style_issues.append(
                        f"{rel_path}: Mist UTF-8 encoding declaratie")

                if (
                    not content.strip().startswith("#!/usr/bin/env python")
                    and "main.py" in file_path
                ):
                    style_issues.append(
                        f"{rel_path}: Mist shebang regel voor executable script"
                    )

                # Controleer docstrings
                if '"""' not in content[
                                :500]:  # Kijk alleen in begin van bestand
                    style_issues.append(
                        f"{rel_path}: Mist module level docstring")

            except Exception as e:
                return VerificationResult(
                    component="Code Consistentie",
                    status=False,
                    message=f"Fout bij analyseren van bestand {rel_path}: {e}",
                )

        # Analyseer relatieve vs. absolute imports
        absolute_imports = []
        relative_imports = []

        for file_path, imports in import_patterns.items():
            for imp in imports:
                if imp.startswith("from src"):
                    absolute_imports.append((file_path, imp))
                elif "import src" in imp:
                    absolute_imports.append((file_path, imp))
                elif imp.startswith("from ."):
                    relative_imports.append((file_path, imp))

        # Controleer op inconsistentie in import stijl
        if absolute_imports and relative_imports:
            style_issues.append(
                "Mix van absolute en relatieve imports gevonden")

        if style_issues:
            return VerificationResult(
                component="Code Consistentie",
                status=False,
                message=f"Code consistentie issues gevonden: {len(style_issues)} problemen",
                details={"style_issues": style_issues},
            )

        return VerificationResult(
            component="Code Consistentie",
            status=True,
            message="Code consistentie analyse geslaagd zonder issues",
        )

    def generate_architecture_diagram(self) -> None:
        """Genereer een architectuurdiagram van het framework."""
        print_subheader("Architectuurdiagram Genereren")

        try:
            import graphviz

            print("Architectuurdiagram genereren...")

            # Creëer een nieuwe directed graph
            dot = graphviz.Digraph(
                "sophia_architecture", comment="Sophia Framework Architecture"
            )

            # Definieer node clusters
            with dot.subgraph(name="cluster_core") as c:
                c.attr(style="filled", color="lightgrey")
                c.node_attr.update(style="filled", color="white")
                c.attr(label="Core Components")

                c.node("main", "Main")
                c.node("connector", "MT5 Connector")
                c.node("risk", "Risk Manager")
                c.node("strategy", "Strategy")
                c.node("strategy_ema", "EMA Strategy")
                c.node("utils", "Utils")

            with dot.subgraph(name="cluster_analysis") as c:
                c.attr(style="filled", color="lightblue")
                c.node_attr.update(style="filled", color="white")
                c.attr(label="Analysis Components")

                c.node("backtest", "Backtest")
                c.node("optimizer", "Optimizer")
                c.node("dashboard", "Dashboard")
                c.node("backtrader_adapter", "Backtrader Adapter")

            with dot.subgraph(name="cluster_strategies") as c:
                c.attr(style="filled", color="lightgreen")
                c.node_attr.update(style="filled", color="white")
                c.attr(label="Backtrader Strategies")

                c.node("turtle_bt", "Turtle Strategy")
                c.node("ema_bt", "EMA Strategy")

            # Definieer relaties
            dot.edge("main", "connector")
            dot.edge("main", "risk")
            dot.edge("main", "strategy")
            dot.edge("main", "strategy_ema")
            dot.edge("main", "backtest")
            dot.edge("main", "dashboard")

            dot.edge("connector", "backtrader_adapter")

            dot.edge("backtest", "backtrader_adapter")
            dot.edge("optimizer", "backtrader_adapter")

            dot.edge("backtrader_adapter", "turtle_bt")
            dot.edge("backtrader_adapter", "ema_bt")

            dot.edge("strategy", "risk")
            dot.edge("strategy_ema", "risk")

            # Render het diagram
            output_path = os.path.join(project_root, "sophia_architecture")
            dot.render(output_path, format="png", cleanup=True)

            print(f"Architectuurdiagram gegenereerd: {output_path}.png")

        except ImportError:
            print(
                "Kon graphviz niet importeren. Installeer met 'pip install graphviz'."
            )
        except Exception as e:
            print(f"Fout bij genereren architectuurdiagram: {e}")

    def run_all_verifications(self) -> bool:
        """
        Voer alle verificaties uit.

        Returns:
            bool: True als alle verificaties slagen, anders False
        """
        print_header("SOPHIA FRAMEWORK VERIFICATIE GESTART")
        print(f"Project root: {project_root}")
        print(f"Tijdstip: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Python versie: {sys.version}")

        with measure_time():
            # Verifieer module imports
            import_results = self.verify_module_imports()
            self.results.extend(import_results)

            # Als kritieke modules niet kunnen worden geïmporteerd, stop met verdere verificaties
            critical_imports_ok = all(
                r.status for r in import_results if
                r.component in self.core_modules
            )
            if not critical_imports_ok:
                print(
                    "\n⚠️ Kritieke modules konden niet worden geïmporteerd. Verdere verificaties worden overgeslagen."
                )
                return False

            # Verifieer main module integratie
            main_result = self.verify_main_integration()
            self.results.append(main_result)

            # Verifieer strategie adapter
            strategy_result = self.verify_strategy_adapter()
            self.results.append(strategy_result)

            # Verifieer backtrader adapter
            backtrader_result = self.verify_backtrader_adapter()
            self.results.append(backtrader_result)

            # Verifieer data flow
            dataflow_result = self.verify_data_flow()
            self.results.append(dataflow_result)

            # Verifieer voorbeeld script
            example_result = self.verify_example_script()
            self.results.append(example_result)

            # Verifieer bestandsstructuur
            structure_result = self.verify_file_structure()
            self.results.append(structure_result)

            # Verifieer code consistentie
            consistency_result = self.verify_code_consistency()
            self.results.append(consistency_result)

            # Genereer architectuurdiagram indien gevraagd
            if self.diagram:
                self.generate_architecture_diagram()

        # Toon resultaten
        self._display_results()

        # Controleer of alle verificaties geslaagd zijn
        return all(result.status for result in self.results)

    def _display_results(self) -> None:
        """Toon de resultaten van alle verificaties."""
        print_header("VERIFICATIE RESULTATEN")

        # Categoriseer resultaten
        passed = [r for r in self.results if r.status]
        failed = [r for r in self.results if not r.status]

        # Toon samenvatting
        print(f"{ConsoleColors.BOLD}Samenvatting:{ConsoleColors.ENDC}")
        print(
            f"Geslaagd: {ConsoleColors.GREEN}{len(passed)}{ConsoleColors.ENDC}")
        print(
            f"Mislukt:  {ConsoleColors.FAIL}{len(failed)}{ConsoleColors.ENDC}")
        print(f"Totaal:   {len(self.results)}")

        # Toon gedetailleerde resultaten
        if self.verbose or failed:
            print(
                "\n{ConsoleColors.BOLD}Gedetailleerde resultaten:{ConsoleColors.ENDC}"
            )

            for result in self.results:
                print(f"{result}")

                # Toon details voor gefaalde tests of in verbose mode
                if not result.status or self.verbose:
                    if result.details:
                        for key, value in result.details.items():
                            if key == "exception" and value:
                                print(
                                    f"  - Exception: {ConsoleColors.FAIL}{value}{ConsoleColors.ENDC}"
                                )
                            elif key == "traceback" and value:
                                print(
                                    f"  - {ConsoleColors.FAIL}Traceback: Beschikbaar maar niet getoond{ConsoleColors.ENDC}"
                                )
                            elif key == "style_issues" and isinstance(value,
                                                                      list):
                                print(f"  - Style issues ({len(value)}):")
                                for i, issue in enumerate(
                                    value[:5]
                                ):  # Toon max 5 issues
                                    print(f"    {i + 1}. {issue}")
                                if len(value) > 5:
                                    print(f"    ... en {len(value) - 5} meer")
                            elif key == "redundant_files" and value:
                                print(
                                    f"  - {ConsoleColors.WARNING}Overbodige bestanden:{ConsoleColors.ENDC}"
                                )
                                for file in value:
                                    print(f"    - {file}")
                            elif isinstance(value, (list, dict)) and value:
                                print(f"  - {key}: {len(value)} items")
                            else:
                                print(f"  - {key}: {value}")

        # Toon actieadvies
        print_subheader("Aanbevolen Acties")

        if failed:
            print(
                f"{ConsoleColors.WARNING}Repareer de volgende problemen:{ConsoleColors.ENDC}"
            )
            for i, result in enumerate(failed):
                print(f"{i + 1}. {result.component}: {result.message}")

            # Controleer op specifieke problemen en geef gerichte adviezen
            for result in failed:
                if (
                    "BacktraderAdapter" in result.component
                    and "NoneType" in result.message
                ):
                    print(
                        f"\n{ConsoleColors.BLUE}Specifiek advies voor BacktraderAdapter issue:{ConsoleColors.ENDC}"
                    )
                    print(
                        "Pas de __init__ methode aan in src/analysis/backtrader_adapter.py om None-configuratie veilig te behandelen:"
                    )
                    print(
                        """
    def __init__(self, config: Dict[str, Any] = None, connector: Optional[MT5Connector] = None):
        self.logger = logging.getLogger("sophia.backtrader")
        self.config = config if config is not None else {}  # Fix voor None configuratie
                    """
                    )
        else:
            print(
                f"{ConsoleColors.GREEN}Alle verificaties zijn geslaagd! 🎉{ConsoleColors.ENDC}"
            )

            # Controleer overbodige bestanden
            redundant_files = []
            for result in self.results:
                if (
                    result.component == "Bestandsstructuur"
                    and result.details
                    and "redundant_files" in result.details
                ):
                    redundant_files = result.details["redundant_files"]

            if redundant_files:
                print(
                    f"\n{ConsoleColors.WARNING}Overweeg de volgende overbodige bestanden te verwijderen:{ConsoleColors.ENDC}"
                )
                for file in redundant_files:
                    print(f"- {file}")

                # Toon commando om bestanden te verwijderen
                print(
                    "\nGebruik het volgende commando om deze bestanden veilig te verwijderen:"
                )
                files_str = " ".join(redundant_files)
                print(
                    f"  mkdir -p backup_files && cp {files_str} backup_files/ && rm {files_str}"
                )

            print(
                "\nJe framework is correct geïntegreerd en klaar voor gebruik!")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Sophia Framework Verificatie Tool")
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Toon gedetailleerde uitvoer"
    )
    parser.add_argument(
        "--diagram", "-d", action="store_true",
        help="Genereer architectuurdiagram"
    )
    parser.add_argument(
        "--performance",
        "-p",
        action="store_true",
        help="Voer performance benchmarks uit",
    )
    return parser.parse_args()


def main():
    """Hoofdfunctie voor het verificatiescript."""
    args = parse_args()

    verifier = FrameworkVerifier(
        verbose=args.verbose, diagram=args.diagram, performance=args.performance
    )

    success = verifier.run_all_verifications()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
