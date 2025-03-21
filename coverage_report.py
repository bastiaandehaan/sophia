#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test coverage analysis for the Sophia Framework.
"""
import os
import subprocess
import sys


def print_header(message):
    """Print a visible header in the console."""
    separator = "=" * 80
    print(f"\n{separator}\n{message}\n{separator}")


def run_coverage():
    """Run tests with coverage and generate a report."""
    print_header("SOPHIA FRAMEWORK TEST COVERAGE")

    # Check if coverage is installed
    try:
        import coverage
    except ImportError:
        print("Coverage package niet gevonden. Installeren...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "coverage"])

    # Create a .coveragerc file
    with open(".coveragerc", "w") as f:
        f.write("[run]\n")
        f.write("source = src\n")
        f.write("omit = */__pycache__/*,*/tests/*,*/venv/*,*/.venv/*\n")

    # Run coverage - simplified with correct paths
    coverage_cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--source=src",
        "-m",
        "pytest",
        "tests/unit",
        "tests/integration",
        "-v",
    ]

    try:
        subprocess.run(coverage_cmd, check=True)
        print("\nTests uitgevoerd, coverage rapport genereren...\n")

        # Generate report
        subprocess.run([sys.executable, "-m", "coverage", "report", "-m"], check=True)

        # Generate HTML report
        html_dir = "coverage_html"
        subprocess.run(
            [sys.executable, "-m", "coverage", "html", "-d", html_dir], check=True
        )

        print(f"\nHTML Coverage rapport gegenereerd in: {html_dir}")

        # Display current coverage percentage
        result = subprocess.run(
            [sys.executable, "-m", "coverage", "report"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Extract percentage from report
        coverage_output = result.stdout.strip().split("\n")
        if len(coverage_output) > 1:
            last_line = coverage_output[-1]
            if "TOTAL" in last_line:
                total_coverage = last_line.split()[-1].strip("%")
                try:
                    coverage_value = float(total_coverage)
                    print(f"\nTotale code coverage: {coverage_value:.1f}%")
                except ValueError:
                    print(f"\nKon coverage percentage niet bepalen: {total_coverage}")

    except subprocess.CalledProcessError as e:
        print(f"Fout bij uitvoeren coverage: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run_coverage())
