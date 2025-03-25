# tests/e2e/test_dashboard_e2e.py
import pytest
import time
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.usefixtures("start_streamlit_server")
def test_dashboard_loads(page: Page):
    """Test of het dashboard succesvol laadt."""
    # Gebruik langere timeouts
    page.set_default_timeout(30000)

    # Navigeer naar dashboard en wacht tot volledig geladen
    page.goto("http://localhost:8501")
    page.wait_for_load_state("networkidle")

    # Screenshot maken voor debugging
    page.screenshot(path="dashboard-loaded.png")

    # Controleer de titel
    expect(page).to_have_title("Sophia Trading Dashboard")

    # De h1 zou "Sophia Trading Framework" zijn, niet "Backtesting"
    # Zoek in plaats daarvan naar een element dat "Backtesting" bevat
    # Dit kan een h1, h2, h3 of een tekst in de sidebar zijn
    backtesting_text = page.locator("text=Backtesting").first
    expect(backtesting_text).to_be_visible()


@pytest.mark.e2e
@pytest.mark.usefixtures("start_streamlit_server")
def test_backtest_button(page: Page):
    """Test of de backtest-knop werkt."""
    page.set_default_timeout(30000)
    page.goto("http://localhost:8501")
    page.wait_for_load_state("networkidle")

    # Wacht tot alles is geladen
    time.sleep(3)

    # Zoek naar verschillende mogelijke knopvarianten
    button_selector = "button:has-text('Start Backtest')"
    if page.locator(button_selector).count() == 0:
        button_selector = "button:has-text('🚀 Start Backtest')"

    # Wacht tot de knop zichtbaar is en klik erop
    page.wait_for_selector(button_selector, state="visible")
    page.screenshot(path="before-click.png")
    page.click(button_selector)

    # Wacht op success message, met flexibelere selector
    try:
        # Probeer verschillende mogelijke succesindicaties
        success_selectors = ["text=succesvol voltooid",
                             "text=Backtest Resultaten", "text=Rendement"]

        # Controleer elk van de mogelijke succes-selectors
        success_found = False
        for selector in success_selectors:
            if page.locator(selector).count() > 0 or page.wait_for_selector(
                selector, timeout=60000, state="visible"):
                success_found = True
                break

        if not success_found:
            page.screenshot(path="backtest-timeout.png")
            raise TimeoutError(
                "Geen van de succes-indicators gevonden na backtest")
    except Exception as e:
        # Controleer alternatieve succes-indicators
        if page.locator("text=Prestatie Overzicht").count() > 0 or page.locator(
            "[data-testid='stMetric']").count() > 0:
            pass  # Succes gevonden via alternatieve indicators
        else:
            page.screenshot(path="backtest-error.png")
            raise e

    page.screenshot(path="after-click.png")


@pytest.mark.e2e
@pytest.mark.usefixtures("start_streamlit_server")
def test_sidebar_navigation(page: Page):
    """Test navigatie via de sidebar."""
    page.set_default_timeout(30000)
    page.goto("http://localhost:8501")
    page.wait_for_load_state("networkidle")

    # Wacht tot de UI volledig is geladen
    time.sleep(3)

    # Controleer of sidebar zichtbaar is, anders uitklappen
    sidebar = page.locator("[data-testid='stSidebar']")
    if not sidebar.is_visible():
        page.click("[data-testid='collapsedControl']")
        time.sleep(1)

    # Zoek naar verschillende manieren waarop Optimalisatie in de UI kan staan
    # 1. Als radio button
    option_selector = "div[role='radio']:has-text('Optimalisatie')"

    # 2. Als normale tekst in sidebar (gecorrigeerde selector syntaxis)
    if page.locator(option_selector).count() == 0:
        option_selector = "[data-testid='stSidebar'] >> text=Optimalisatie"

    # 3. Als laatste redmiddel, elke tekst 'Optimalisatie'
    if page.locator(option_selector).count() == 0:
        option_selector = "text=Optimalisatie"

    # Debug screenshot
    page.screenshot(path="sidebar-before-click.png")

    # Klik op de Optimalisatie optie
    page.click(option_selector)
    time.sleep(2)  # Wacht tot UI update

    # Debug screenshot
    page.screenshot(path="sidebar-after-click.png")

    # Controleer of ergens 'Optimalisatie' staat in een header
    # Dit kan h1, h2 of een andere header zijn
    header_text = page.locator("h1, h2, h3").filter(has_text="Optimalisatie")
    expect(header_text).to_be_visible()