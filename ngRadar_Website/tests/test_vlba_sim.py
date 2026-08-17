from unittest.mock import patch, MagicMock
from ngRadar_Website.enums import Stations, Status


# =============================================
# TEST THE STANDALONE FUNCTIONS FROM DSOC_SIM
# =============================================

# ==============================================================================
# IMPORTANT:
# Because we read "ngrok_endpoint.env" on import, we need to patch the Path globally
# before importing all the functions we want to test.
# ==============================================================================
mock_env_data = "BOOTSTRAP_SERVER=localhost:9092\nSOME_OTHER_VAR=value" 
with patch("pathlib.Path.read_text", return_value=mock_env_data):
    from ngRadar_Website.management.commands.vlba_sim import (
        send_kafka_message,
        record_transfer_event,
        process_msg,
    )

    
# ==============================================================================
# 1. send_kafka_message Test
# ==============================================================================

@patch("ngRadar_Website.management.commands.vlba_sim.produce")
@patch("ngRadar_Website.management.commands.vlba_sim.datetime")
def test_send_kafka_message(mock_datetime, mock_produce):
    producer_topic="test_topic"
    producer_config="test_config"
    transfer_uuid="test_transfer_uuid"
    gbt_uuid="test_gbt_uuid"
    status=Status.TRANSFERRING
    num_bytes=2048

    mock_produce.return_value = None

    fake_datetime = MagicMock()
    fake_datetime.isoformat.return_value = "2026-08-12T12:34:56+00:00"
    mock_datetime.now.return_value = fake_datetime

    send_kafka_message(
        producer_topic=producer_topic,
        producer_config=producer_config,
        transfer_uuid=transfer_uuid,
        gbt_uuid=gbt_uuid,
        status=status,
        num_bytes=num_bytes,
    )

    mock_produce.assert_called_once_with(
        producer_topic,
        producer_config,
        str(transfer_uuid),
        '{"transfer_uuid": "test_transfer_uuid", "gbt_uuid": "test_gbt_uuid", "status": 4, "status_label": "Transferring", "num_bytes": 2048, "filename": null, "event_time": "2026-08-12T12:34:56+00:00", "message": "", "stations": "Hancock (25-m, VLBA)"}',
    )