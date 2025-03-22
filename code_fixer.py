#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script om UTF-8 encoding declaraties toe te voegen aan Python-bestanden.
"""
import os


def add_encoding_declarations(project_root):
    """Voeg UTF-8 encoding declaraties toe aan Python-bestanden."""
    encoding_declaration = "# -*- coding: utf-8 -*-\n"
    files_to_fix = [
        os.path.join(project_root, "src", "strategy.py"),
        os.path.join(project_root, "src", "strategy_ema.py"),
        os.path.join(project_root, "src", "utils.py"),
        os.path.join(project_root, "src", "__init__.py"),
        os.path.join(project_root, "src", "analysis", "__init__.py"),
        # Voeg hier andere bestanden toe uit de foutrapportage
    ]

    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            print(f"Bestand niet gevonden: {file_path}")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Voeg encoding declaratie toe als deze ontbreekt
        if "# -*- coding: utf-8 -*-" not in content:
            content = encoding_declaration + content

            # Schrijf bijgewerkte inhoud terug
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ Encoding declaratie toegevoegd aan: {file_path}")
        else:
            print(f"⏩ Bestand al correct: {file_path}")


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    add_encoding_declarations(project_root)
    print("Encoding declaraties toegevoegd aan alle bestanden!")
