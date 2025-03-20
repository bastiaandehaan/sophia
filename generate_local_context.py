#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sophy Trading Framework - Dynamische Projectdocumentatie Generator
Genereert een gestructureerd document met projectarchitectuur en codeoverzicht
Geoptimaliseerd voor beperkte uitvoergrootte
"""

import datetime
import glob

# Configuratie
import os
import re

USER_HOME = os.path.expanduser("~")
LOCAL_DIR = os.path.join(USER_HOME, "PycharmProjects", "Sophy")
REPO_NAME = "Sophy"
OUTPUT_FILE = f"{REPO_NAME}_local_context.txt"


def ensure_dir(directory):
    """Controleer of de map bestaat en navigeer er naartoe"""
    if not os.path.exists(directory):
        print(f"Error: De map {directory} bestaat niet.")
        exit(1)
    os.chdir(directory)


def init_output_file():
    """Initialiseer het uitvoerbestand"""
    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
            print(f"Verwijderen van bestaand bestand: {OUTPUT_FILE}")
        except Exception as e:
            print(f"Error: Kon het bestaande bestand niet verwijderen: {e}")
            exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# {REPO_NAME} Project Documentatie\n")
        f.write(
            f"Gegenereerd op: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )


def write_to_file(content):
    """Voeg content toe aan het uitvoerbestand"""
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(content)


def count_files(directory_path, pattern="*.py", exclude="__init__.py"):
    """Tel het aantal bestanden in een map volgens patroon"""
    count = 0
    for file in glob.glob(os.path.join(directory_path, pattern)):
        if exclude and os.path.basename(file) == exclude:
            continue
        count += 1
    return count


def generate_architecture():
    """Genereer architectuurdocumentatie"""
    content = "# Sophy Trading Framework Architectuur\n"
    content += (
        f"Gegenereerd op: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )

    # Modules detecteren
    content += "## Kernmodules\n\n"
    content += "| Module | Beschrijving | Componenten |\n"
    content += "|--------|-------------|-------------|\n"

    modules = [
        {"path": "src/connector", "name": "Connector", "desc": "MT5 marktverbinding"},
        {"path": "src/strategy", "name": "Strategy", "desc": "Trading strategieën"},
        {"path": "src/risk", "name": "Risk", "desc": "Risicomanagement"},
        {
            "path": "src/analysis",
            "name": "Analysis",
            "desc": "Backtesting & optimalisatie",
        },
        {"path": "src/ftmo", "name": "FTMO", "desc": "FTMO compliance"},
        {"path": "src/utils", "name": "Utils", "desc": "Hulpfuncties & tools"},
        {
            "path": "src/presentation",
            "name": "Presentation",
            "desc": "Visualisatie & dashboards",
        },
    ]

    for module in modules:
        if os.path.exists(module["path"]):
            count = count_files(module["path"])
            content += (
                f"| **{module['name']}** | {module['desc']} | {count} componenten |\n"
            )

    content += "\n"

    # Architectuurdiagram
    content += "## Architectuurdiagram\n\n"
    content += "```mermaid\n"
    content += "graph TD\n"
    content += "    Main[Main Application] --> Connector\n"
    content += "    Main --> Strategy\n"
    content += "    Main --> Risk\n"
    content += "    Main --> Analysis\n"
    content += "    Main --> FTMO\n"
    content += "    Main --> Utils\n"

    # Strategie-implementaties detecteren
    if os.path.exists("src/strategy"):
        content += "    Strategy --> StrategyFactory[Strategy Factory]\n"
        content += "    StrategyFactory --> BaseStrategy[Base Strategy]\n"

        for file in glob.glob("src/strategy/*.py"):
            base_name = os.path.basename(file)
            if base_name not in [
                "__init__.py",
                "base_strategy.py",
                "strategy_factory.py",
            ]:
                strategy_name = os.path.splitext(base_name)[0]
                content += f"    BaseStrategy --> {strategy_name}\n"

    # Risicomanagement componenten
    if os.path.exists("src/risk"):
        content += "    Risk --> PositionSizer[Position Sizer]\n"
        content += "    Risk --> RiskManager[Risk Manager]\n"

    # Analyse componenten
    if os.path.exists("src/analysis"):
        content += "    Analysis --> Backtester[Backtester]\n"
        content += "    Analysis --> Optimizer[Optimizer]\n"

        if os.path.exists("src/analysis/backtrader_adapter.py") or os.path.exists(
            "src/analysis/backtrader_integration.py"
        ):
            content += (
                "    Analysis --> BacktraderIntegration[Backtrader Integration]\n"
            )

    content += "```\n\n"

    # Configuratie-overzicht
    if os.path.exists("config"):
        content += "## Configuratie\n\n"
        content += "Het systeem gebruikt de volgende configuratiebestanden:\n\n"

        for config_file in glob.glob("config/*.json"):
            config_name = os.path.basename(config_file)
            content += f"- **{config_name}**\n"

        content += "\n"

    # Test-infrastructuur
    unit_tests = len(glob.glob("tests/unit/test_*.py"))
    integration_tests = len(glob.glob("tests/integration/test_*.py"))

    if unit_tests > 0 or integration_tests > 0:
        content += "## Test Infrastructuur\n\n"
        content += "| Test Type | Aantal |\n"
        content += "|-----------|--------|\n"
        content += f"| Unit Tests | {unit_tests} |\n"
        content += f"| Integratie Tests | {integration_tests} |\n\n"

    write_to_file(content)


def generate_toc():
    """Genereer inhoudsopgave"""
    content = "# Inhoudsopgave\n\n"

    categories = [
        {"name": "Kernmodules", "pattern": r"src/(connector|strategy|risk)"},
        {"name": "Analyse", "pattern": r"src/analysis"},
        {"name": "FTMO", "pattern": r"src/ftmo"},
        {"name": "Utils", "pattern": r"src/utils"},
        {"name": "Configuratie", "pattern": r"config"},
        {"name": "Tests", "pattern": r"tests"},
        {"name": "Documentatie", "pattern": r"docs"},
    ]

    for category in categories:
        content += f"## {category['name']}\n\n"

        pattern = re.compile(category["pattern"])
        files_found = False

        for ext in ["py", "json"]:
            for file in glob.glob(f"**/*.{ext}", recursive=True):
                if "__pycache__" in file or "egg-info" in file:
                    continue

                if pattern.search(file):
                    files_found = True
                    anchor = file.replace("/", "-").replace("\\", "-")
                    content += f"- [{file}](#{anchor})\n"

        if not files_found:
            content += "- *Geen bestanden gevonden*\n"

        content += "\n"

    write_to_file(content)


def process_file(file_path, category="Overig"):
    """Verwerk een bestand en voeg het toe aan de documentatie"""
    # Skip te grote of irrelevante bestanden
    if any(
        x in file_path
        for x in ["__pycache__", "egg-info", ".git", ".idea", "local_context.txt"]
    ):
        return

    file_size = os.path.getsize(file_path)

    # Skip te grote bestanden
    if file_size > 50000:
        print(f"Skipping grote file ({file_size} bytes): {file_path}")
        content = f"## {category}: {file_path}\n\n"
        content += f"*Bestand overgeslagen vanwege grootte ({file_size} bytes)*\n\n"
        content += "-----------\n\n"
        write_to_file(content)
        return

    print(f"Processing file: {file_path}")

    content = f"## {category}: {file_path}\n\n"

    # Bepaal bestandsextensie en taal
    extension = os.path.splitext(file_path)[1][1:].lower()

    language_map = {
        "toml": "toml",
        "md": "markdown",
        "r": "r",
        "rmd": "r",
        "py": "python",
        "json": "json",
        "yml": "yaml",
        "yaml": "yaml",
        "txt": "plaintext",
    }

    language = language_map.get(extension, "plaintext")

    content += f"```{language}\n"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content += f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                content += f.read()
        except Exception as e:
            content += f"Error reading file: {str(e)}\n"

    content += "\n```\n\n"
    content += "-----------\n\n"

    write_to_file(content)


def process_categories():
    """Verwerk bestanden per categorie"""
    content = "# Bestandsinhoud\n\n"
    write_to_file(content)

    file_categories = {
        "src/connector": "Market Connectivity",
        "src/strategy": "Trading Strategy",
        "src/risk": "Risk Management",
        "src/analysis": "Analysis & Backtesting",
        "src/ftmo": "FTMO Compliance",
        "src/utils": "Utilities",
        "src/presentation": "Visualization",
        "config": "Configuration",
        "tests": "Testing",
        "docs": "Documentation",
    }

    for prefix, category in file_categories.items():
        if os.path.exists(prefix):
            content = f"## {category} Modules\n\n"
            write_to_file(content)

            for ext in ["py", "json", "md", "txt"]:
                for file in glob.glob(f"{prefix}/**/*.{ext}", recursive=True):
                    if "__pycache__" not in file and "egg-info" not in file:
                        process_file(file, category)

    # Verwerk belangrijke overige bestanden
    content = "## Overige Bestanden\n\n"
    write_to_file(content)

    key_files = [
        "setup.py",
        "requirements.txt",
        "run.py",
        "verify_sophy.py",
        ".gitignore",
    ]
    for file in key_files:
        if os.path.exists(file):
            process_file(file, "Systeembestanden")


def main():
    """Hoofdfunctie"""
    print(f"Sophy Project Documentation Generator")
    print(f"-------------------------------------")

    # Controleer en navigeer naar de projectmap
    ensure_dir(LOCAL_DIR)

    # Initialiseer uitvoerbestand
    init_output_file()

    # Genereer architectuurdocumentatie
    print("Genereren van architectuurdocumentatie...")
    generate_architecture()

    # Genereer inhoudsopgave
    print("Genereren van inhoudsopgave...")
    generate_toc()

    # Verwerk bestandsinhoud
    print("Verwerken van bestandsinhoud...")
    process_categories()

    # Output verificatie
    file_size = os.path.getsize(OUTPUT_FILE)
    print("")
    print(f"Projectdocumentatie gegenereerd: {OUTPUT_FILE} ({file_size} bytes)")
    print("")
    print("PyCharm Tip: Voeg '*local_context.txt' toe aan de uitsluitingspatterns")
    print("in Settings > Project Structure > Exclude files")


if __name__ == "__main__":
    main()
