from pathlib import Path

from dotenv import load_dotenv
from unittest.mock import patch, MagicMock

from ngRadar_Website.views.views import get_obs_events
from ngRadar_Website.enums import Stations
from datetime import datetime, timezone, timedelta
import pytest
from ngRadar_Website.enums import Stations
from ngRadar_Website.models.models import gbtEvent, dsocEvent, ObservatoryEvent, uiEvent
from ngRadar_Website.views.views import get_obs_events

import random,string

# # ==============================================================================
# # IMPORTANT:
# # Because we read "ngrok_endpoint.env" on import, we need to patch the Path globally
# # before importing all the functions we want to test.
# # ==============================================================================
# mock_env_data = "BOOTSTRAP_SERVER=localhost:9092\nSOME_OTHER_VAR=value" 
# with patch("pathlib.Path.read_text", return_value=mock_env_data):
#     from ngRadar_Website.views.views import (
#         get_obs_events,
#         get_Message_Latency,
#         latency_graphing,
#         serve_image,
#         lock_status,
#         submit_waveform,
#     )

#Test the Functions from views.py
@pytest.mark.django_db
def test_get_obs_events():

    now = datetime.now(timezone.utc)

    for i in range(25):
        ObservatoryEvent.objects.create(
            uuid = f"{i}",
            object_id = f"OBJ{i}",
            target = "target",
            tx_waveform = "Sinewave",
            rec_waveform = "Sinewave",
            product_type = "DDM",
            product_id = f"00{i}",
            station = Stations.GBT,
            event_time = now - timedelta(seconds=i),
            created_at = now - timedelta(seconds=i+5),
            xmit_station = Stations.GBT,
            rcvr_station = Stations.DSOC,
            image_key = f"ddm/target/uuid.png",
            num_bytes = 2048,
            latency_ms = 100,
        )
        gbtEvent.objects.create(
            uuid = f"{i}",
            object_id = f"OBJ{i}",
            target = "target",
            tx_waveform = "Sinewave",
            rec_waveform = "Sinewave",
            event_time = now - timedelta(seconds=i),
            latency_ms = 100
        )
        dsocEvent.objects.create(
            uuid = f"{i}",
            object_id = f"OBJ{i}",
            target = "target",
            image_key = f"ddm/target/uuid.png",
            num_bytes = 2048,
            event_time = now - timedelta(seconds=i),
            latency_ms = 100
        )
        uiEvent.objects.create(
            uuid = f"{i}",
            selected_waveform = "Sinewave",
            event_time = now - timedelta(seconds=i)
        )

    theObservatoryEvents = get_obs_events()

    latest_obs_events = theObservatoryEvents["latest_events"]
    length = len(latest_obs_events)
    assert length == 20


def getMockObsEvent(mockID, mockTarget, mockWaveform, currentDate, mock_latency):
    obs_event = {
        "object_id":mockID,
        "target":mockTarget,
        "tx_waveform":mockWaveform,   # Included for GBT
        "rec_waveform":mockWaveform, # Included for GBT
        "image_key":None,                     # GBT records do not have images
        "num_bytes":None,                     # GBT records do not have images
        "event_time":currentDate,
        "latency_ms":mock_latency,
        "station":Stations.GBT,      
        "xmit_station":Stations.GBT, 
        "rcvr_station":Stations.DSOC
        }
    return obs_event

#function below generates a mock UUID - used AI to generate this function
def gen_pattern_uuid_like():
    # Allowed characters: digits + lowercase letters
    alphabet = string.ascii_lowercase + string.digits

    # Pattern: 9c85a7c7-0506-44f3-9792-63b1867c6f97
    # Segment lengths: 8-4-4-4-12
    seg1 = ''.join(random.choice(alphabet) for _ in range(8))
    seg2 = ''.join(random.choice(alphabet) for _ in range(4))
    seg3 = ''.join(random.choice(alphabet) for _ in range(4))
    seg4 = ''.join(random.choice(alphabet) for _ in range(4))
    seg5 = ''.join(random.choice(alphabet) for _ in range(12))

    return f"{seg1}-{seg2}-{seg3}-{seg4}-{seg5}"

def gen_8char_ID():
    alphabet = string.ascii_letters + string.digits  # A-Z a-z 0-9
    return ''.join(random.choice(alphabet) for _ in range(8))

def getMockGBTEvent(mockID,mockTarget,mockWaveform,currentDate,mock_latency,mockUUID):
    gbt_evt = {
    "uuid" : mockUUID,
    "object_id" : mockID,
    "target" : mockTarget,
    "tx_waveform" : mockWaveform,
    "rec_waveform" : mockWaveform,
    "event_time" : currentDate,
    "latency_ms": mock_latency
    }
    return gbt_evt

def getMockDSOCEvent(mockID, mockTarget,currentDate,mock_latency,mockUUID, mockBytes):
    dsoc_evt = {
    "uuid" : mockUUID,
    "object_id" : mockID,
    "target" : mockTarget,
    "image_key" : mockID,
    "num_bytes" : mockBytes,
    "event_time" : currentDate,
    "latency_ms" : mock_latency
    }
    return dsoc_evt

def getMockUIEvent(mockUUID,mockWaveform,currentDate):
    ui_evt = {
    "uuid" : mockUUID,
    "selected_waveform" : mockWaveform,
    "event_time" : currentDate
    }
    return ui_evt