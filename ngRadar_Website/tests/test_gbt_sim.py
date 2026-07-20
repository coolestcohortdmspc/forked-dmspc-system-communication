from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


# =============================================
# TEST THE STANDALONE FUNCTIONS FROM GBT_SIM
# =============================================

# ==============================================================================
# IMPORTANT:
# Because we read "ngrok_endpoint.env" on import, we need to patch the Path globally
# before importing all the functions we want to test.
# ==============================================================================
mock_env_data = "BOOTSTRAP_SERVER=localhost:9092\nSOME_OTHER_VAR=value" 
with patch("pathlib.Path.read_text", return_value=mock_env_data):
    from ngRadar_Website.management.commands.gbt_sim import (
        set_payload_dict,
        generate_payload,
        turn_off_transmitter,
        publish_to_db,
        produce,
        process_msg,
    )

# ==============================================================================
# 1. set_payload_dict Test
# ==============================================================================

#patching the function called within set_payload_dict to use a fake output:
@patch("ngRadar_Website.management.commands.gbt_sim.latency_calc")
def test_set_payload_dict(mock_latency):

    #fake variable setup:
    payload = {
        "object_id": None, 
        "target": None, 
        "tx_waveform": None, 
        "rec_waveform": None, 
        "event_time": None, 
        "latency_ms": None,
    }
    
    waveform = "sinewave"
    event_time = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

    mock_latency.return_value = 100

    #creating a range of times around event_time to have reasonable error bars:
    before = datetime.now(timezone.utc)
    payload = set_payload_dict(waveform, event_time)
    after = datetime.now(timezone.utc)

    #assert that the function correctly changed the payload values:
    assert payload["object_id"] == '30104'
    assert payload["target"] == 'Moretus'
    assert payload["tx_waveform"] == waveform
    assert payload["rec_waveform"] == waveform
    assert before <= payload["event_time"] <= after
    mock_latency.assert_called_once_with(payload["event_time"], event_time)