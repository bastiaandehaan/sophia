# tests/e2e/test_dashboard_e2e.py
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.usefixtures("start_streamlit_server")
def test_dashboard_loads(page: Page):
    """Test of het dashboard succesvol laadt."""
    page.goto("http://localhost:8501")
    expect(page).to_have_title("Sophia Trading Dashboard")
    header = page.locator("h1")
    expect(header).to_contain_text("Backtesting")  # Verwacht "🧪 Backtesting" in de UI


@pytest.mark.e2e
@pytest.mark.usefixtures("start_streamlit_server")
def test_backtest_button(page: Page):
    """Test of de backtest-knop werkt."""
    page.goto("http://localhost:8501")
    page.click("button:has-text('Start Backtest')")  # Precieze locator voor Streamlit-knop
    success_msg = page.locator("text=✅ Backtest succesvol voltooid!")
    expect(success_msg).to_be_visible(timeout=15000)  # 15 sec timeout voor subprocess


@pytest.mark.e2e
@pytest.mark.usefixtures("start_streamlit_server")
def test_sidebar_navigation(page: Page):
    """Test navigatie via de sidebar."""
    page.goto("http://localhost:8501")
    page.click("text=Optimalisatie")  # Klik op sidebar-optie
    header = page.locator("h1")
    expect(header).to_contain_text("Optimalisatie")  # Verwacht "⚙️ Optimalisatie" in de UI