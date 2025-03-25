# tests/e2e/conftest.py
import pytest
import subprocess
import time
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("e2e_tests")


@pytest.fixture(scope="session")
def start_streamlit_server():
    """Start de Streamlit-server als fixture met verbeterde robuustheid."""
    # Vind het dashboard bestand
    project_root = Path(__file__).parent.parent.parent
    possible_paths = [
        project_root / "src" / "backtesting" / "dashboard.py",
        project_root / "src" / "dashboard.py",
        project_root / "dashboard.py"
    ]

    dashboard_path = None
    for path in possible_paths:
        if path.exists():
            dashboard_path = path
            break

    if not dashboard_path:
        raise FileNotFoundError(
            f"Dashboard bestand niet gevonden! Gezocht in: {[str(p) for p in possible_paths]}")

    logger.info(f"Streamlit server starten met dashboard: {dashboard_path}")

    # Start Streamlit als subprocess met verbeterde opties
    process = subprocess.Popen(
        ["streamlit", "run", str(dashboard_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wacht langer tot de server is opgestart (10 seconden)
    logger.info("Wachten tot server is opgestart (10 seconden)...")
    time.sleep(10)

    # Controleer of proces nog draait
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        raise RuntimeError(
            f"Streamlit server is voortijdig gestopt: \nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}")

    logger.info("Streamlit server draait en is klaar voor tests")
    yield

    # Teardown: server afsluiten na tests
    logger.info("Tests afgerond, Streamlit server afsluiten...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    logger.info("Streamlit server succesvol afgesloten")


@pytest.fixture
def setup_page(page):
    """Voorbereiding van Playwright page met langere timeouts."""
    page.set_default_timeout(30000)  # 30 seconden
    page.set_default_navigation_timeout(60000)  # 60 seconden
    return page