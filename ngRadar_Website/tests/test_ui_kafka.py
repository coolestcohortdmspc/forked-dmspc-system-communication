from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from unittest.mock import ANY

import pytest
from ngRadar_Website.enums import Stations, Message
from uuid import uuid4

from ngRadar_Website.ui_kafka import (
    consume_ui_events,
)

# ==============================================================================
# 1. consume_ui_events Test
# ==============================================================================

@patch("ngRadar_Website.ui_kafka.Consumer")
@patch("ngRadar_Website.ui_kafka.os.getenv")
def test_consume_ui_events(mock_getenv, mock_Consumer):

    mock_getenv.side_effect = lambda key, default=None: {
    "UI_KAFKA_TOPICS": "fake_topic1,fake_topic2",
    "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
    "UI_KAFKA_GROUP_ID": "test-ui-group",
    }.get(key, default)

    mock_consumer = mock_Consumer.return_value

    mock_consumer.poll.side_effect = [
        None,
        RuntimeError("Stop test"),
    ]

    with pytest.raises(RuntimeError, match="Stop test"):
        consume_ui_events()

    mock_consumer.subscribe.assert_called_once()