#!/usr/bin/env python3
# run_e2e_tests.py
import subprocess
import sys
import time
import os
from pathlib import Path
import argparse


def find_dashboard_path():
    """Vind het pad naar het dashboard bestand."""
    project_root = Path(__file__).parent
    possible_paths = [
        project_root / "src" / "backtesting" / "dashboard.py",
        project_root / "src" / "dashboard.py",
        project_root / "dashboard.py"
    ]

    for path in possible_paths:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Dashboard bestand niet gevonden! Gezocht in: {[str(p) for p in possible_paths]}")


def main():
    parser = argparse.ArgumentParser(
        description="Run Streamlit dashboard E2E tests")
    parser.add_argument("--headed", action="store_true",
                        help="Run tests in headed mode (visible browser)")
    parser.add_argument("--test", type=str,
                        help="Specific test to run (e.g. test_dashboard_loads)")
    args = parser.parse_args()

    dashboard_path = find_dashboard_path()
    print(f"Found dashboard at: {dashboard_path}")

    print("Starting Streamlit server...")
    streamlit_process = subprocess.Popen(
        ["streamlit", "run", str(dashboard_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        print("Waiting for server to start...")
        time.sleep(10)

        print("Running tests...")
        test_cmd = ["python", "-m", "pytest", "tests/e2e/test_dashboard_e2e.py",
                    "-v"]

        if args.headed:
            test_cmd.append("--headed")

        if args.test:
            test_cmd.append(f"tests/e2e/test_dashboard_e2e.py::{args.test}")

        print(f"Command: {' '.join(test_cmd)}")
        test_process = subprocess.run(test_cmd, check=False)

        if test_process.returncode != 0:
            print("Tests failed!")
            sys.exit(test_process.returncode)
        else:
            print("All tests passed!")

    finally:
        print("Shutting down server...")
        streamlit_process.terminate()
        try:
            streamlit_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Server didn't terminate gracefully, forcing...")
            streamlit_process.kill()


if __name__ == "__main__":
    main()