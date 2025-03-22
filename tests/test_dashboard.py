# File: tests/test_dashboard.py

from unittest.mock import patch, MagicMock

from src.analysis.dashboard import main, SophiaDashboard


def test_main_function_initializes_dashboard():
    with patch("src.analysis.dashboard.tk.Tk") as mock_tk:
        with patch("src.analysis.dashboard.SophiaDashboard") as mock_dashboard:
            mock_root = MagicMock()
            mock_tk.return_value = mock_root

            main()

            mock_tk.assert_called_once()
            mock_dashboard.assert_called_once_with(mock_root)
            mock_root.mainloop.assert_called_once()


def test_sophia_dashboard_initialization():
    root_mock = MagicMock()

    # Mock de load_config methode om een lege config te retourneren
    with patch.object(SophiaDashboard, 'load_config', return_value={}):
        dashboard = SophiaDashboard(root_mock)

        assert dashboard is not None
        assert isinstance(dashboard, SophiaDashboard)

        # Controleer of belangrijke UI-elementen zijn aangemaakt
        assert hasattr(dashboard, 'notebook')
        assert hasattr(dashboard, 'backtest_tab')
        assert hasattr(dashboard, 'optimize_tab')
        assert hasattr(dashboard, 'live_tab')
        assert hasattr(dashboard, 'config_tab')


def test_run_batch_backtests_no_symbols_selected():
    """Test dat de batch functie correct reageert wanneer geen symbolen zijn geselecteerd."""
    root_mock = MagicMock()

    with patch.object(SophiaDashboard, 'load_config', return_value={}):
        dashboard = SophiaDashboard(root_mock)

        # Mock messagebox.showwarning
        with patch(
            'src.analysis.dashboard.messagebox.showwarning') as mock_warning:
            # Setup: simuleer dat geen symbolen zijn geselecteerd
            dashboard.batch_symbols_list = MagicMock()
            dashboard.batch_symbols_list.curselection.return_value = []

            # Actie: functie aanroepen
            dashboard.run_batch_backtests()

            # Assertie: controleer of waarschuwing wordt getoond
            mock_warning.assert_called_once_with("Batch Test",
                                                 "Selecteer minstens één symbool")


def test_run_batch_backtests_no_timeframes_selected():
    """Test dat de batch functie correct reageert wanneer wel symbolen maar geen timeframes zijn geselecteerd."""
    root_mock = MagicMock()

    with patch.object(SophiaDashboard, 'load_config', return_value={}):
        dashboard = SophiaDashboard(root_mock)

        # Mock messagebox.showwarning
        with patch(
            'src.analysis.dashboard.messagebox.showwarning') as mock_warning:
            # Setup: simuleer dat wel symbolen maar geen timeframes zijn geselecteerd
            dashboard.batch_symbols_list = MagicMock()
            dashboard.batch_symbols_list.curselection.return_value = [
                0]  # Eén symbool geselecteerd
            dashboard.batch_symbols_list.get.return_value = "EURUSD"

            dashboard.batch_timeframes_list = MagicMock()
            dashboard.batch_timeframes_list.curselection.return_value = []  # Geen timeframes geselecteerd

            # Actie: functie aanroepen
            dashboard.run_batch_backtests()

            # Assertie: controleer of waarschuwing wordt getoond
            mock_warning.assert_called_once_with("Batch Test",
                                                 "Selecteer minstens één timeframe")


def test_run_batch_backtests_valid_selection():
    """Test dat de batch functie correct werkt met geldige selecties."""
    root_mock = MagicMock()

    with patch.object(SophiaDashboard, 'load_config', return_value={}):
        dashboard = SophiaDashboard(root_mock)

        # Mock de benodigde UI-elementen en methoden
        dashboard.batch_symbols_list = MagicMock()
        dashboard.batch_symbols_list.curselection.return_value = [0,
                                                                  1]  # Twee symbolen geselecteerd
        dashboard.batch_symbols_list.get.side_effect = ["EURUSD", "USDJPY"]

        dashboard.batch_timeframes_list = MagicMock()
        dashboard.batch_timeframes_list.curselection.return_value = [0,
                                                                     2]  # Twee timeframes geselecteerd
        dashboard.batch_timeframes_list.get.side_effect = ["M15", "H4"]

        dashboard.backtest_strategy_var = MagicMock()
        dashboard.backtest_strategy_var.get.return_value = "turtle"

        dashboard.backtest_period_var = MagicMock()
        dashboard.backtest_period_var.get.return_value = "1y"

        # Mock strategie-parameters
        dashboard.backtest_entry_period_var = MagicMock(get=lambda: "20")
        dashboard.backtest_exit_period_var = MagicMock(get=lambda: "10")
        dashboard.backtest_atr_period_var = MagicMock(get=lambda: "14")

        # Mock de toplevel window
        with patch('src.analysis.dashboard.tk.Toplevel') as mock_toplevel:
            toplevel_instance = MagicMock()
            mock_toplevel.return_value = toplevel_instance

            # Mock Text widget en Scrollbar
            mock_text = MagicMock()
            with patch('src.analysis.dashboard.tk.Text',
                       return_value=mock_text):
                with patch('src.analysis.dashboard.ttk.Scrollbar'):
                    # Mock threading om te voorkomen dat daadwerkelijke threads worden gestart
                    with patch(
                        'src.analysis.dashboard.threading.Thread') as mock_thread:
                        # Uitvoeren van de functie
                        dashboard.run_batch_backtests()

                        # Controles
                        mock_toplevel.assert_called_once()
                        mock_thread.assert_called_once()
                        # Controleer of de thread wordt gestart met de juiste parameters
                        args, kwargs = mock_thread.call_args
                        assert kwargs['target'] == dashboard._run_batch_tests
                        assert "turtle" in kwargs['args']  # Strategie
                        assert kwargs['args'][1] == ["EURUSD",
                                                     "USDJPY"]  # Symbolen
                        assert kwargs['args'][2] == ["M15", "H4"]  # Timeframes


def test_buttons_not_duplicated():
    """Test dat er geen dubbele knoppen zijn in de backtest tab."""
    root_mock = MagicMock()

    with patch.object(SophiaDashboard, 'load_config', return_value={}), \
        patch('src.analysis.dashboard.ttk.Button') as mock_button, \
        patch('src.analysis.dashboard.ttk.Frame', return_value=MagicMock()):
        # De calls naar pack() moeten gemockt worden om te voorkomen dat een
        # AttributeError optreedt, omdat MagicMock niet de pack-methode heeft
        mock_button.return_value = MagicMock()

        dashboard = SophiaDashboard(root_mock)

        # Controleer dat er exact één "Start Backtest" knop is gemaakt
        start_backtest_calls = [
            call_args for call_args in mock_button.call_args_list
            if call_args[1].get('text') == "Start Backtest"
        ]

        # Er moet precies één "Start Backtest" knop zijn
        assert len(
            start_backtest_calls) == 1, "Er moet precies één 'Start Backtest' knop zijn"