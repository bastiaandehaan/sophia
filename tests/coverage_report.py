# tests/coverage_report.py
# !/usr/bin/env python3
"""
Test coverage analyse voor het Sophia Framework.

Dit script voert de tests uit en genereert een coverage rapport.
Gebruik: python tests/coverage_report.py
"""
import os
import subprocess
import sys

# Voeg project root toe aan sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def print_header(message):
    """Print een opvallende header in de console."""
    separator = "=" * 80
    print(f"\n{separator}\n{message}\n{separator}")


def run_coverage():
    """Voer de tests uit met coverage en genereer een rapport."""
    print_header("SOPHIA FRAMEWORK TEST COVERAGE")

    # Controleer of coverage is geïnstalleerd
    try:
        import coverage
    except ImportError:
        print("Coverage package niet gevonden. Installeren...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "coverage"])

    # Configureer coverage
    cov_config = {"source": ["src"],
        "omit": ["*/__pycache__/*", "*/tests/*", "*/venv/*"]}

    # Maak een .coveragerc bestand
    with open(os.path.join(project_root, ".coveragerc"), "w") as f:
        f.write("[run]\n")
        f.write(f"source = {','.join(cov_config['source'])}\n")
        f.write(f"omit = {','.join(cov_config['omit'])}\n")

    # Voer coverage uit
    coverage_cmd = [sys.executable, "-m", "coverage", "run", "--source=src", "-m",
        "pytest", "tests/", "-v"]

    try:
        subprocess.run(coverage_cmd, check=True)
        print("\nTests uitgevoerd, coverage rapport genereren...\n")

        # Genereer rapport
        subprocess.run([sys.executable, "-m", "coverage", "report", "-m"], check=True)

        # Genereer HTML rapport
        html_dir = os.path.join(project_root, "coverage_html")
        subprocess.run([sys.executable, "-m", "coverage", "html", "-d", html_dir],
            check=True)

        print(f"\nHTML Coverage rapport gegenereerd in: {html_dir}")

        # Toon huidige coverage percentage
        result = subprocess.run([sys.executable, "-m", "coverage", "report"],
            capture_output=True, text=True, check=True)

        # Haal percentage uit rapport
        coverage_output = result.stdout.strip().split('\n')
        if len(coverage_output) > 1:
            last_line = coverage_output[-1]
            if 'TOTAL' in last_line:
                total_coverage = last_line.split()[-1].strip('%')
                coverage_value = float(total_coverage)

                print(f"\nTotale code coverage: {coverage_value:.1f}%")

                if coverage_value >= 90:
                    print_header("DOEL BEHAALD: ≥90% CODE COVERAGE")
                else:
                    missing = 90 - coverage_value
                    print_header(
                        f"DOEL NIET BEHAALD: {coverage_value:.1f}% (nog {missing:.1f}% nodig voor 90%)")

    except subprocess.CalledProcessError as e:
        print(f"Fout bij uitvoeren coverage: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run_coverage())