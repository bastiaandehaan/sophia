#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SophiaScan: Intelligent Trading Framework Analyzer

Een geavanceerde tool die je Sophia Trading Framework project
doorlicht en belangrijke inzichten geeft.
"""

import argparse
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List


# ANSI-kleuren voor rijke console-output
class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"

    @staticmethod
    def blue(text):
        return f"{Colors.BLUE}{text}{Colors.END}"

    @staticmethod
    def green(text):
        return f"{Colors.GREEN}{text}{Colors.END}"

    @staticmethod
    def yellow(text):
        return f"{Colors.YELLOW}{text}{Colors.END}"

    @staticmethod
    def red(text):
        return f"{Colors.RED}{text}{Colors.END}"

    @staticmethod
    def bold(text):
        return f"{Colors.BOLD}{text}{Colors.END}"


@dataclass
class ComponentInfo:
    """Informatie over een project component."""

    path: str
    imports: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    quality_score: float = 0.0


@dataclass
class ProjectScan:
    """Resultaten van een complete project scan."""

    components: Dict[str, ComponentInfo] = field(default_factory=dict)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    integration_score: float = 0.0
    structure_score: float = 0.0
    performance_warnings: List[str] = field(default_factory=list)


def parse_arguments():
    """Parse command line arguments for output control."""
    parser = argparse.ArgumentParser(
        description="Sophia Trading Framework Analyzer")
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Toon gedetailleerde output"
    )
    parser.add_argument(
        "--summary", "-s", action="store_true", help="Toon alleen samenvatting"
    )
    parser.add_argument(
        "--issues",
        "-i",
        action="store_true",
        help="Toon alleen problemen en aanbevelingen",
    )
    parser.add_argument("--output", "-o", type=str,
                        help="Sla output op naar bestand")
    return parser.parse_args()


class SophiaScan:
    """Intelligente analyzer voor het Sophia Trading Framework."""

    def __init__(self, project_root: str = None):
        """
        Initialiseer de scanner.

        Args:
            project_root: Pad naar de project root. Als None, wordt huidige map gebruikt.
        """
        # Detecteer project root
        if project_root is None:
            self.project_root = self._detect_project_root()
        else:
            self.project_root = project_root

        # Zorg dat project root in sys.path staat
        if self.project_root not in sys.path:
            sys.path.insert(0, self.project_root)

        # Verwachte structuur van het project
        self.expected_core_modules = ["connector", "risk", "utils"]
        self.expected_strategy_modules = ["turtle_strategy", "ema_strategy"]
        self.expected_backtest_modules = ["backtest", "backtrader_adapter",
                                          "dashboard"]
        self.expected_bt_strategy_modules = ["turtle_bt", "ema_bt"]

        # Resultaten van de scan
        self.scan_results = ProjectScan()

        # Patroon om imports te herkennen
        self.import_pattern = re.compile(
            r"^(?:from\s+([^\s]+)(?:\s+import\s+([^\s]+))?|import\s+([^\s]+))"
        )

    def _detect_project_root(self) -> str:
        """Detecteer automatisch de project root directory."""
        current_dir = os.path.abspath(os.path.dirname(__file__))

        # Zoek naar een map met src/ en examples/
        while current_dir != os.path.dirname(current_dir):  # Stop bij root
            if os.path.exists(
                os.path.join(current_dir, "src")) and os.path.exists(
                os.path.join(current_dir, "examples")
            ):
                return current_dir
            current_dir = os.path.dirname(current_dir)

        # Fallback naar de huidige map
        return os.path.abspath(os.path.dirname(__file__))

    def _find_python_files(self, directory: str) -> List[str]:
        """Zoek alle Python bestanden in een directory."""
        python_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))
        return python_files

    def _analyze_file(self, file_path: str) -> ComponentInfo:
        """Analyseer een enkel Python bestand."""
        rel_path = os.path.relpath(file_path, self.project_root)
        component = ComponentInfo(path=rel_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extraheer imports
            imports = []
            for line in content.split("\n"):
                match = self.import_pattern.match(line.strip())
                if match:
                    module = match.group(1) or match.group(3)
                    if module:
                        imports.append(module)
            component.imports = imports

            # Zoek naar functies en klassen
            function_pattern = re.compile(r"def\s+([^\s(]+)")
            class_pattern = re.compile(r"class\s+([^\s(:]+)")

            component.functions = [
                m.group(1) for m in function_pattern.finditer(content)
            ]
            component.classes = [m.group(1) for m in
                                 class_pattern.finditer(content)]

            # Eenvoudige code kwaliteitscheck
            quality_issues = []

            # Check op docstrings
            if '"""' not in content[:500]:
                quality_issues.append("Mist module-level docstring")

            # Check op lange functies (> 50 regels)
            current_func = None
            line_count = 0
            long_functions = []

            for line in content.split("\n"):
                func_match = function_pattern.match(line.strip())
                if func_match:
                    if current_func and line_count > 50:
                        long_functions.append(current_func)
                    current_func = func_match.group(1)
                    line_count = 0
                elif current_func:
                    line_count += 1

            if current_func and line_count > 50:
                long_functions.append(current_func)

            if long_functions:
                quality_issues.append(
                    f"Lange functies gevonden: {', '.join(long_functions)}"
                )

            # Bereken simpele code kwaliteitsscore (0-100)
            score = 100
            if len(quality_issues) >= 1:
                score -= 10 * len(quality_issues)
            if len(long_functions) >= 1:
                score -= 5 * len(long_functions)

            component.quality_score = max(0, score)
            component.issues = quality_issues

        except Exception as e:
            component.issues.append(f"Fout bij analyse: {str(e)}")
            component.quality_score = 0

        return component

    def scan_project(self):
        """Voer een complete scan uit van het project."""
        start_time = time.time()
        print(
            f"{Colors.bold('SophiaScan')}: Project analyseren in {Colors.blue(self.project_root)}"
        )

        # Scan src directory
        src_dir = os.path.join(self.project_root, "src")
        if not os.path.exists(src_dir):
            self.scan_results.issues.append("Src directory niet gevonden")
            return self.scan_results

        # Vind alle Python bestanden
        python_files = self._find_python_files(self.project_root)
        print(
            f"  {Colors.blue(str(len(python_files)))} Python bestanden gevonden")

        # Analyseer alle bestanden parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            components = list(executor.map(self._analyze_file, python_files))

        # Sla componentinformatie op
        for component in components:
            self.scan_results.components[component.path] = component

        # Bouw dependency graph
        self._build_dependency_graph()

        # Controleer structuur
        self._verify_project_structure()

        # Controleer integratie
        self._verify_integration()

        # Bereken project scores
        self._calculate_project_scores()

        # Controleer op mogelijke prestatieproblemen
        self._detect_performance_issues()

        elapsed_time = time.time() - start_time
        print(f"Scan voltooid in {elapsed_time:.2f} seconden")

        return self.scan_results

    def _build_dependency_graph(self):
        """Bouw een graph van module afhankelijkheden."""
        dependency_graph = {}

        for path, component in self.scan_results.components.items():
            module_name = os.path.splitext(path)[0].replace(os.path.sep, ".")
            dependencies = []

            for imp in component.imports:
                if imp.startswith("src"):
                    dependencies.append(imp)

            dependency_graph[module_name] = dependencies

        self.scan_results.dependency_graph = dependency_graph

    def _verify_project_structure(self):
        """Verifieer dat de projectstructuur voldoet aan de verwachtingen."""
        # Controleer core modules
        missing_core = []
        for module in self.expected_core_modules:
            path = os.path.join("src", "core", f"{module}.py")
            if path not in self.scan_results.components:
                missing_core.append(module)

        if missing_core:
            self.scan_results.issues.append(
                f"Ontbrekende core modules: {', '.join(missing_core)}"
            )

        # Controleer strategiemodules
        missing_strategies = []
        for module in self.expected_strategy_modules:
            path = os.path.join("src", "strategies", f"{module}.py")
            if path not in self.scan_results.components:
                missing_strategies.append(module)

        if missing_strategies:
            self.scan_results.issues.append(
                f"Ontbrekende strategie modules: {', '.join(missing_strategies)}"
            )

        # Controleer backtest modules
        missing_backtest = []
        for module in self.expected_backtest_modules:
            path = os.path.join("src", "backtesting", f"{module}.py")
            if path not in self.scan_results.components:
                missing_backtest.append(module)

        if missing_backtest:
            self.scan_results.issues.append(
                f"Ontbrekende backtest modules: {', '.join(missing_backtest)}"
            )

        # Controleer backtrader strategie modules
        missing_bt_strategies = []
        for module in self.expected_bt_strategy_modules:
            path = os.path.join("src", "backtesting", "strategies",
                                f"{module}.py")
            if path not in self.scan_results.components:
                missing_bt_strategies.append(module)

        if missing_bt_strategies:
            self.scan_results.issues.append(
                f"Ontbrekende backtrader strategie modules: {', '.join(missing_bt_strategies)}"
            )

    def _verify_integration(self):
        """Verifieer dat de verschillende componenten correct geïntegreerd zijn."""
        # Controleer of main module verwijst naar core en backtesting modules
        main_path = os.path.join("src", "main.py")
        if main_path in self.scan_results.components:
            main_component = self.scan_results.components[main_path]

            # Controleer core imports
            core_imports = [imp for imp in main_component.imports if
                            "core" in imp]
            if not core_imports:
                self.scan_results.issues.append(
                    "Main module importeert geen core modules"
                )

            # Controleer backtesting imports
            backtest_imports = [
                imp for imp in main_component.imports if "backtesting" in imp
            ]
            if not backtest_imports:
                self.scan_results.issues.append(
                    "Main module importeert geen backtesting modules"
                )

        # Controleer of backtesting modules verwijzen naar core modules
        for path, component in self.scan_results.components.items():
            if "backtesting" in path and path != os.path.join(
                "src", "backtesting", "__init__.py"
            ):
                core_imports = [imp for imp in component.imports if
                                "core" in imp]
                if not core_imports and "backtrader_adapter" in path:
                    self.scan_results.issues.append(
                        f"{path} mist core module imports")

    def _calculate_project_scores(self):
        """Bereken algemene kwaliteitsscores voor het project."""
        # Bereken gemiddelde code kwaliteit
        quality_scores = [
            c.quality_score for c in self.scan_results.components.values()
        ]
        avg_quality = sum(quality_scores) / len(
            quality_scores) if quality_scores else 0

        # Bereken structuurscore
        structure_score = 100
        # Verminder score voor elke structuur- of integratieprobleem
        structure_score -= len(self.scan_results.issues) * 15

        # Bereken integratiescore
        integration_score = 100
        # Verminder score voor integratieproblemen
        integration_issues = [
            issue for issue in self.scan_results.issues if "importeert" in issue
        ]
        integration_score -= len(integration_issues) * 20

        # Sla scores op
        self.scan_results.structure_score = max(0, structure_score)
        self.scan_results.integration_score = max(0, integration_score)

    def _detect_performance_issues(self):
        """Identificeer mogelijke prestatieproblemen."""
        # Zoek naar complexe algoritmen of potentieel inefficiënte code
        for path, component in self.scan_results.components.items():
            # Controleer op geneste lussen
            with open(
                os.path.join(self.project_root, path),
                "r",
                encoding="utf-8",
                errors="replace",
            ) as f:
                content = f.read()
                content_lines = content.split("\n")
                indent_levels = []

                for i, line in enumerate(content_lines):
                    if re.search(r"\s*for\s+.*\s+in\s+.*:", line) or re.search(
                        r"\s*while\s+.*:", line
                    ):
                        indent = len(line) - len(line.lstrip())

                        # Check voor geneste lus
                        if any(prev_indent < indent for prev_indent in
                               indent_levels):
                            with_function = "onbekende functie"

                            # Zoek de functie waarin dit voorkomt
                            for j in range(i, -1, -1):
                                if re.search(r"def\s+([^\s(]+)",
                                             content_lines[j]):
                                    match = re.search(
                                        r"def\s+([^\s(]+)", content_lines[j]
                                    )
                                    with_function = match.group(1)
                                    break

                            self.scan_results.performance_warnings.append(
                                f"Geneste lus gevonden in {path} in functie {with_function} (regel ~{i + 1})"
                            )
                            break

                        indent_levels.append(indent)

            # Controleer op grote datastructuren
            with open(
                os.path.join(self.project_root, path),
                "r",
                encoding="utf-8",
                errors="replace",
            ) as f:
                content = f.read()
                # Zoek naar lange lijst of dictionary definities
                for match in re.finditer(
                    r"(list|dict|set|tuple)\([^)]{1000,}", content
                ):
                    self.scan_results.performance_warnings.append(
                        f"Grote datastructuur gevonden in {path}"
                    )
                    break

    def print_summary(self):
        """Print a very brief summary of key findings."""
        # Calculate scores
        quality_scores = [
            c.quality_score for c in self.scan_results.components.values()
        ]
        avg_quality = sum(quality_scores) / len(
            quality_scores) if quality_scores else 0
        overall_score = (
                            self.scan_results.structure_score
                            + self.scan_results.integration_score
                            + avg_quality
                        ) / 3

        print("=" * 40)
        print(f"{Colors.bold('SOPHIA SCAN SAMENVATTING')}")
        print("=" * 40)
        print(f"Bestanden gescand: {len(self.scan_results.components)}")
        print(f"Problemen gevonden: {len(self.scan_results.issues)}")
        print(
            f"Prestatie waarschuwingen: {len(self.scan_results.performance_warnings)}"
        )

        low_quality_count = len(
            [c for c in self.scan_results.components.values() if
             c.quality_score < 70]
        )
        print(f"Componenten met lage kwaliteit: {low_quality_count}")
        print(f"Totaalscore: {int(overall_score)}/100")

        # Top issues if any exist
        if self.scan_results.issues:
            print("\nBelangrijkste problemen:")
            for i, issue in enumerate(self.scan_results.issues[:3], 1):
                print(f"  {i}. {issue}")

        # Top recommendations if needed
        if self.scan_results.issues or self.scan_results.performance_warnings:
            print("\nAanbevelingen:")
            recommendations = []
            if any(
                "core modules" in issue for issue in self.scan_results.issues):
                recommendations.append("Fix ontbrekende core modules")
            if any("importeert" in issue for issue in self.scan_results.issues):
                recommendations.append("Verbeter module integratie")
            if self.scan_results.performance_warnings:
                recommendations.append("Optimaliseer geneste lussen")
            if low_quality_count > 0:
                recommendations.append("Voeg ontbrekende docstrings toe")

            for i, rec in enumerate(recommendations[:3], 1):
                print(f"  {i}. {rec}")

    def print_issues(self):
        """Print alleen de gevonden problemen en aanbevelingen."""
        print("=" * 60)
        print(f"{Colors.bold('SOPHIA SCAN PROBLEMEN')}")
        print("=" * 60)

        # Print issues
        if self.scan_results.issues:
            print(f"\n{Colors.bold('Structuur- en Integratieproblemen:')}")
            for i, issue in enumerate(self.scan_results.issues, 1):
                print(f"  {Colors.red(str(i))}. {issue}")
        else:
            print(
                f"\n{Colors.green('Geen structuur- of integratieproblemen gevonden!')}"
            )

        # Print performance warnings summary
        if self.scan_results.performance_warnings:
            print(
                f"\n{Colors.bold('Prestatieproblemen:')} {len(self.scan_results.performance_warnings)} gevonden"
            )
            for i, warning in enumerate(
                self.scan_results.performance_warnings[:5], 1):
                print(f"  {Colors.yellow(str(i))}. {warning}")

            if len(self.scan_results.performance_warnings) > 5:
                print(
                    f"  ... en {len(self.scan_results.performance_warnings) - 5} meer"
                )

        # Low quality components summary
        low_quality = [
            (p, c)
            for p, c in self.scan_results.components.items()
            if c.quality_score < 70
        ]
        if low_quality:
            print(
                f"\n{Colors.bold('Componenten met Lage Kwaliteitsscore:')} {len(low_quality)} gevonden"
            )
            for i, (path, component) in enumerate(
                sorted(low_quality, key=lambda x: x[1].quality_score)[:5], 1
            ):
                print(
                    f"  {Colors.yellow(str(i))}. {path} (Score: {component.quality_score:.0f}/100)"
                )
                for issue in component.issues[
                             :2]:  # Show max 2 issues per component
                    print(f"     - {issue}")

            if len(low_quality) > 5:
                print(
                    f"  ... en {len(low_quality) - 5} meer componenten met lage score"
                )

        # Recommendations
        self._print_recommendations()

    def print_report(self, args=None):
        """Print a filtered report based on command-line arguments."""
        if args:
            if args.summary:
                self.print_summary()
                return
            elif args.issues:
                self.print_issues()
                return

            # For verbose output or default, continue with full report

        # Default report (medium verbosity)
        print("\n" + "=" * 60)
        print(f"{Colors.bold('SOPHIA TRADING FRAMEWORK SCAN RAPPORT')}")
        print("=" * 60)

        # Calculate overall scores
        quality_scores = [
            c.quality_score for c in self.scan_results.components.values()
        ]
        avg_quality = sum(quality_scores) / len(
            quality_scores) if quality_scores else 0
        overall_score = (
                            self.scan_results.structure_score
                            + self.scan_results.integration_score
                            + avg_quality
                        ) / 3

        # Print scores first for quick overview
        print("\n" + "-" * 40)
        print(f"{Colors.bold('Projectscores:')}")
        print(
            f"  Structuur:    {self._format_score(self.scan_results.structure_score)}"
        )
        print(
            f"  Integratie:   {self._format_score(self.scan_results.integration_score)}"
        )
        print(f"  Codekwaliteit: {self._format_score(avg_quality)}")
        print(
            f"\n{Colors.bold('ALGEMENE BEOORDELING:')} {self._format_score(overall_score)}"
        )
        print("-" * 40)

        # Print issues
        if self.scan_results.issues:
            print(f"\n{Colors.bold('Gevonden Problemen:')}")
            for i, issue in enumerate(self.scan_results.issues, 1):
                print(f"  {Colors.red(str(i))}. {issue}")
        else:
            print(
                f"\n{Colors.green('Geen structuur- of integratieproblemen gevonden!')}"
            )

        # Print performance warnings summary
        if self.scan_results.performance_warnings:
            print(
                f"\n{Colors.bold('Prestatieproblemen:')} {len(self.scan_results.performance_warnings)} gevonden"
            )
            # Show only first few warnings
            for i, warning in enumerate(
                self.scan_results.performance_warnings[:3], 1):
                print(f"  {Colors.yellow(str(i))}. {warning}")

            if len(self.scan_results.performance_warnings) > 3:
                print(
                    f"  ... en {len(self.scan_results.performance_warnings) - 3} meer"
                )

        # Print low quality components summary
        low_quality = [
            (p, c)
            for p, c in self.scan_results.components.items()
            if c.quality_score < 70
        ]
        if low_quality:
            print(
                f"\n{Colors.bold('Componenten met Lage Kwaliteitsscore:')} {len(low_quality)} gevonden"
            )
            # Show only first few components
            for i, (path, component) in enumerate(
                sorted(low_quality, key=lambda x: x[1].quality_score)[:3], 1
            ):
                print(
                    f"  {Colors.yellow(str(i))}. {path} (Score: {component.quality_score:.0f}/100)"
                )
                for issue in component.issues:
                    print(f"     - {issue}")

            if len(low_quality) > 3:
                print(
                    f"  ... en {len(low_quality) - 3} meer componenten met lage score"
                )

        # Always print recommendations
        print(f"\n{Colors.bold('Aanbevelingen:')}")
        self._print_recommendations()

    def _format_score(self, score: float) -> str:
        """Formatteer een score met kleurcodering."""
        score_int = int(score)
        if score_int >= 90:
            return f"{Colors.green(f'{score_int}/100')} Uitstekend"
        elif score_int >= 75:
            return f"{Colors.green(f'{score_int}/100')} Goed"
        elif score_int >= 60:
            return f"{Colors.yellow(f'{score_int}/100')} Redelijk"
        else:
            return f"{Colors.red(f'{score_int}/100')} Aandacht nodig"

    def _print_recommendations(self):
        """Print aanbevelingen op basis van scanresultaten."""
        if not self.scan_results.issues and not self.scan_results.performance_warnings:
            print(
                f"  {Colors.green('✓')} Je project ziet er goed uit! Ga zo door.")
            return

        recommendations = []

        # Aanbevelingen op basis van problemen
        if any("core modules" in issue for issue in self.scan_results.issues):
            recommendations.append("Zorg dat alle core modules aanwezig zijn")

        if any("importeert" in issue for issue in self.scan_results.issues):
            recommendations.append(
                "Verbeter module-integratie door juiste imports toe te voegen"
            )

        # Aanbevelingen voor prestatie
        if self.scan_results.performance_warnings:
            recommendations.append(
                "Overweeg geneste lussen te optimaliseren voor betere prestaties"
            )

        # Aanbevelingen voor lage kwaliteit
        low_quality = [
            (p, c)
            for p, c in self.scan_results.components.items()
            if c.quality_score < 70
        ]
        if low_quality:
            recommendations.append(
                "Verbeter documentatie en codekwaliteit in modules met lage score"
            )

        # Print alle aanbevelingen
        for i, recommendation in enumerate(recommendations, 1):
            print(f"  {i}. {recommendation}")

        print(
            f"\n  {Colors.bold('TIP:')} Gebruik deze scan regelmatig tijdens ontwikkeling om problemen vroeg te detecteren."
        )


def main():
    """Hoofdfunctie voor het scannen van een project."""
    # Parse arguments for output control
    args = parse_arguments()

    # Automatisch project root detecteren
    scanner = SophiaScan()

    # Scan het project
    scanner.scan_project()

    # Print het rapport met filtering
    if args.output:
        # Redirect output to file
        import sys

        original_stdout = sys.stdout
        with open(args.output, "w", encoding="utf-8") as f:
            sys.stdout = f
            scanner.print_report(args)
            sys.stdout = original_stdout
        print(f"Rapport opgeslagen in: {args.output}")
    else:
        # Print to console
        scanner.print_report(args)


if __name__ == "__main__":
    main()
