import os
from datetime import datetime


def export_project(root_dir, output_file, extensions=None, exclude_dirs=None,
                   max_file_size=50000, summary_length=20):
    """
    Exporteer projectstructuur en bestandsinhoud naar een tekstbestand.

    Args:
        root_dir: Root directory van het project
        output_file: Uitvoerbestand
        extensions: Bestandsextensies om te includeren (standaard: ['.py'])
        exclude_dirs: Directories om uit te sluiten
        max_file_size: Maximum bestandsgrootte om volledig te exporteren (in bytes)
        summary_length: Aantal regels aan begin en einde van grote bestanden te tonen
    """
    if extensions is None:
        extensions = ['.py']
    if exclude_dirs is None:
        exclude_dirs = [
            '.idea', '.venv', '__pycache__', 'backtest_results',
            'optimization_results', 'logs', 'coverage_html'
        ]

    # Belangrijke bestanden die altijd volledig moeten worden opgenomen
    core_files = [
        'main.py',
        'connector.py',
        'risk.py',
        'strategy.py',
        'strategy_ema.py',
        'backtrader_adapter.py'
    ]

    # Bestanden die volledig kunnen worden overgeslagen
    skip_files = [
        '__init__.py',
        'coverage_report.py',
        'verify_sophia.py'
    ]

    with open(output_file, 'w', encoding='utf-8') as f:
        # Projectbeschrijving
        f.write("===== SOPHIA TRADING FRAMEWORK PROJECT OVERVIEW =====\n")
        f.write(
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Projectstructuur - compactere weergave
        f.write("===== PROJECT STRUCTURE =====\n")
        structure = {}

        for root, dirs, files in os.walk(root_dir):
            # Sla uitgesloten mappen over
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            # Filter relevante bestanden
            relevant_files = [file for file in files if
                              any(file.endswith(ext) for ext in extensions)]

            if relevant_files:
                rel_path = os.path.relpath(root, root_dir)
                if rel_path == '.':
                    rel_path = 'root'
                structure[rel_path] = relevant_files

        # Gestructureerde weergave van mappen en bestanden
        for directory, files in sorted(structure.items()):
            f.write(f"{directory}/\n")
            for file in sorted(files):
                f.write(f"  ├── {file}\n")
            f.write("\n")

        # Bestandsinhoud - selectiever en beknopter
        f.write("\n===== KEY FILE CONTENTS =====\n")

        # Teller voor statistieken
        processed_files = 0
        skipped_files = 0
        large_files = 0

        for directory, files in sorted(structure.items()):
            for file in sorted(files):
                # Sla bepaalde bestanden over
                if file in skip_files and file not in core_files:
                    skipped_files += 1
                    continue

                file_path = os.path.join(root_dir, directory, file)
                if directory == 'root':
                    file_path = os.path.join(root_dir, file)

                try:
                    # Controleer bestandsgrootte
                    file_size = os.path.getsize(file_path)

                    # Volledig exporteren voor kernbestanden of kleine bestanden
                    is_core_file = any(
                        core_name in file_path for core_name in core_files)
                    if is_core_file or file_size <= max_file_size:
                        processed_files += 1
                        f.write(
                            f"\n===== {file_path} [{file_size} bytes] =====\n")

                        with open(file_path, 'r',
                                  encoding='utf-8') as file_content:
                            content = file_content.read()
                            f.write(content)
                            f.write("\n")
                    else:
                        # Voor grote bestanden, toon alleen een samenvatting
                        large_files += 1
                        f.write(
                            f"\n===== {file_path} [{file_size} bytes - SUMMARY] =====\n")

                        with open(file_path, 'r',
                                  encoding='utf-8') as file_content:
                            lines = file_content.readlines()

                            # Aantal modules/klassen/functies tellen
                            class_count = sum(1 for line in lines if
                                              line.strip().startswith('class '))
                            def_count = sum(1 for line in lines if
                                            line.strip().startswith('def '))

                            f.write(
                                f"File contains {len(lines)} lines, {class_count} classes, {def_count} functions\n\n")

                            # Begin van het bestand
                            f.write("--- BEGINNING OF FILE ---\n")
                            f.write(''.join(lines[:summary_length]))
                            f.write("\n[...]\n")

                            # Einde van het bestand
                            if len(lines) > summary_length * 2:
                                f.write("--- END OF FILE ---\n")
                                f.write(''.join(lines[-summary_length:]))

                except Exception as e:
                    f.write(f"\n===== {file_path} =====\n")
                    f.write(f"Error reading file: {e}\n")

        # Statistieken toevoegen
        f.write(f"\n\n===== EXPORT STATISTICS =====\n")
        f.write(f"Files fully exported: {processed_files}\n")
        f.write(f"Files summarized: {large_files}\n")
        f.write(f"Files skipped: {skipped_files}\n")
        f.write(
            f"Total files processed: {processed_files + large_files + skipped_files}\n")

    return processed_files, large_files, skipped_files


if __name__ == "__main__":
    project_root = "."
    output_file = "sophia_project_summary.txt"
    processed, summarized, skipped = export_project(
        project_root,
        output_file,
        extensions=['.py'],
        max_file_size=30000,  # 30KB maximum voor volledige export
        summary_length=15  # 15 regels aan begin en einde
    )

    print(f"Project export voltooid naar: {output_file}")
    print(f"Statistieken:")
    print(f"- Volledig geëxporteerde bestanden: {processed}")
    print(f"- Samengevatte grote bestanden: {summarized}")
    print(f"- Overgeslagen bestanden: {skipped}")
