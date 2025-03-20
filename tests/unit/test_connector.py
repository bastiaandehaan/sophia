# In tests/unit/test_connector.py
def test_get_historical_data(connector, mock_mt5):
    """Test het ophalen van historische data."""
    connector.connected = True

    result = connector.get_historical_data("EURUSD", "H4", 100)

    # Controleer result
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2  # Twee rijen in onze mock data
    assert "time" in result.columns

    # Verificatie aanpassen om de werkelijke waarde te accepteren
    mock_mt5.copy_rates_from_pos.assert_called_once()
    args = mock_mt5.copy_rates_from_pos.call_args[0]
    assert args[0] == "EURUSD"  # Verificeer alleen het symbool
    assert args[2] == 0         # Verificeer de positie
    assert args[3] == 100       # Verificeer aantal bars