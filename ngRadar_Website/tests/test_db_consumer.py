from unittest.mock import patch, MagicMock
from ngRadar_Website.models.models import ObservatoryEvent
from ngRadar_Website.enums import Message, Stations
import json

# ==============================================================================
# IMPORTANT:
# Because we read "ngrok_endpoint.env" on import, we need to patch the Path globally
# before importing all the functions we want to test.
# ==============================================================================
mock_env_data = "BOOTSTRAP_SERVER=localhost:9092\nSOME_OTHER_VAR=value" 
with patch("pathlib.Path.read_text", return_value=mock_env_data):
    from ngRadar_Website.management.commands.db_consumer import (
        process_msg,
        record_obs_event,
        publish_db_committed,
    )

# ==============================================================================
# 1. process_msg Test
# ==============================================================================

@patch("ngRadar_Website.management.commands.db_consumer.record_obs_event")
@patch("ngRadar_Website.management.commands.db_consumer.publish_db_committed")
@patch("ngRadar_Website.management.commands.db_consumer.transaction")
def test_process_msg(mock_transaction, mock_publish, mock_record):
    """Scenario 1: the 'try' is successful"""

    msg = MagicMock()

    payload = {
        "gbt_uuid": "fake_uuid",
        "transfer_uuid": "12345",
    }

    msg.value.return_value = json.dumps(payload).encode("utf-8")
    
    msg.key.return_value = str(
        Message.DSOC_RESPOND_STORAGE.value
    ).encode("utf-8")

    msg.topic.return_value = "fake topic"

    # Make `with transaction.atomic():` work
    mock_transaction.atomic.return_value.__enter__.return_value = None

    # Make transaction.on_commit execute the callback
    mock_transaction.on_commit.side_effect = (
        lambda callback: callback()
    )

    result = process_msg(msg, "fake topic", "fake config")

    mock_publish.assert_called_once_with(topic="fake topic",
                        producer_config="fake config",
                        payload=payload)
    mock_record.assert_called_once_with(payload)
    assert result == True