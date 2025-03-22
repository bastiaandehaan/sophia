import glob
import os
from datetime import datetime


def export_sophia_dashboard(output_file="sophia_dashboard_focus.txt"):
    """
    Intelligente export van Sophia framework bestanden die zich aanpast aan
    de werkelijke projectstructuur.
    """
    # Detecteer automatisch waar we belangrijke bestanden kunnen vinden
    print("Scanning for Sophia project files...")

    # Padzoekpatronen - zowel voor Windows als Unix stijl paden
    search_patterns = [
        # Dashboard zoekpatronen
        "**/dashboard.py",
        "**/src/analysis/dashboard.py",
        "**/analysis/dashboard.py",

        # Backtest gerelateerde bestanden
        "**/backtest.py",
        "**/backtrader_adapter.py",
        "**/optimizer.py",

        # Core bestanden
        "**/connector.py",
        "**/strategy.py",
        "**/strategy_ema.py",
        "**/risk.py",
        "**/utils.py",

        # Configuratie
        "**/settings.json",
        "**/config/settings.json"
    ]

    # Gevonden bestanden en belangrijke mappen
    found_files = []
    key_directories = set()

    # Zoek bestanden met de wildcard patronen
    for pattern in search_patterns:
        matches = glob.glob(pattern, recursive=True)
        for match in matches:
            # Normaliseer pad en voeg toe aan gevonden bestanden
            normalized_path = os.path.normpath(match)
            if os.path.isfile(normalized_path):
                found_files.append(normalized_path)
                # Voeg directory toe aan sleuteldirectories
                dir_path = os.path.dirname(normalized_path)
                key_directories.add(dir_path)
                parent_dir = os.path.dirname(dir_path)
                if parent_dir:
                    key_directories.add(parent_dir)

    # Begin export naar bestand
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("===== SOPHIA DASHBOARD FOCUSED ANALYSIS =====\n")
        f.write(
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Projectinformatie
        f.write("===== PROJECT INFORMATION =====\n")
        f.write(f"Current working directory: {os.getcwd()}\n")
        f.write(f"Files found: {len(found_files)}\n")
        f.write(f"Key directories identified: {len(key_directories)}\n\n")

        # Exporteer gevonden bestanden
        f.write("===== KEY FILE CONTENTS =====\n")
        if not found_files:
            f.write(
                "No relevant files found. Please run this script from the Sophia project directory.\n")

        for file_path in sorted(found_files):
            try:
                file_size = os.path.getsize(file_path)
                f.write(f"\n===== {file_path} [{file_size} bytes] =====\n")

                with open(file_path, 'r', encoding='utf-8') as file_content:
                    content = file_content.read()
                    f.write(content)
                    f.write("\n\n")

            except Exception as e:
                f.write(f"Error reading file {file_path}: {e}\n")

        # Directory structuur
        f.write("\n===== DISCOVERED PROJECT STRUCTURE =====\n")
        for directory in sorted(key_directories):
            f.write(f"\n{directory}/ Contents:\n")
            try:
                for item in sorted(os.listdir(directory)):
                    item_path = os.path.join(directory, item)
                    if os.path.isfile(item_path):
                        f.write(f"  ├── {item}\n")
                    else:
                        f.write(f"  ├── {item}/ (directory)\n")
            except Exception as e:
                f.write(f"  Error listing directory: {e}\n")


if __name__ == "__main__":
    print("Sophia Dashboard Analysis Tool")
    print("------------------------------")
    output_file = "../../AppData/Roaming/JetBrains/PyCharm2024.3/scratches/sophia_dashboard_focus.txt"

    export_sophia_dashboard(output_file)

    print(f"Export compleet: {output_file}")
    print("Controleer de inhoud voor dashboard en gerelateerde bestanden.")