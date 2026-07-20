from datetime import datetime, timedelta, timezone
from ngRadar_Website.utils import latency_calc, config_func, bootstrap
import pytest
from unittest.mock import patch, MagicMock
from ngRadar_Website.enums import Stations


# ===============================================
# Here we can test all of our utility functions
# ===============================================


# ==============================================================================
# 1. latency_calc
# ==============================================================================

#can add as many different latency test values here as you want:
@pytest.mark.parametrize("event_time, expected", [
        (datetime.now(timezone.utc) - timedelta(seconds=1), 1000),
        (datetime.now(timezone.utc) - timedelta(seconds=2), 2000)
    ])
def test_latency_calc(event_time, expected):
    latency = latency_calc(event_time)

    upper_bound = expected+100
    
    # 3. Assert (1 second = 1000 milliseconds)
    assert expected <= latency < upper_bound, f"Expected latency around 1000 ms, got {latency} ms"


# ==============================================================================
# 2. config_func
# ==============================================================================

# NOTE I attempted to make these two scenarios into one test with parametrize, but because they have a different number of variables/outputs, it was too awkward

@patch("ngRadar_Website.utils.AdminClient")
def test_config_func_GBT(mock_AdminClient):
    """Scenario 1: sim is GBT"""

    #dealing with the create_topic function, which calls f.result:
    future = MagicMock()
    future.result.return_value = None
    
    mock_admin = mock_AdminClient.return_value
    mock_admin.create_topics.return_value = {
        "user_input": future,
        "GBT_data": future,
    }

    sim = Stations.GBT
    bootstrap = "12345"

    producer_topic, producer_config, consumer_topic, consumer_config = config_func(sim, bootstrap)

    assert producer_topic == "GBT_data"
    assert producer_config == {
            "bootstrap.servers": bootstrap,
            "message.max.bytes": 8388608,
            "client.id": "GBT-producer"
        }
    assert consumer_topic == "user_input"
    assert consumer_config == {
            "bootstrap.servers": bootstrap,
            "fetch.max.bytes": 8388608,
            "session.timeout.ms": 45000,
            "client.id": "GBT-consumer",
            "group.id": "GBT-consumer-group",
            "auto.offset.reset": "earliest",
        }
    mock_AdminClient.assert_called_once_with(
        {"bootstrap.servers": bootstrap}
    )


def test_config_func_DSOC():
    """Scenario 2: sim is DSOC"""

    sim = Stations.DSOC
    bootstrap = "12345"

    topic, config = config_func(sim, bootstrap)

    assert topic == ["GBT_data"]
    assert config == {
            "bootstrap.servers": bootstrap,
            "fetch.max.bytes": 8388608,
            "session.timeout.ms": 45000,
            "client.id": "dsoc-consumer",
            "group.id": "consumer-group",
            "auto.offset.reset": "earliest",
        }
