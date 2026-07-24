import pytest
from unittest.mock import patch, MagicMock

from ngRadar_Website.views.views import get_obs_events
from ngRadar_Website.enums import Stations
from datetime import datetime, timezone

import random,string, MockQuery

#constants
RECORDS_TO_DISPLAY=20
LAST_RECORDS = 5

#Test the Functions from views.py
@patch("ngRadar_Website.views.views.ObservatoryEvent")
@patch("ngRadar_Website.views.views.gbtEvent")
@patch("ngRadar_Website.views.views.dsocEvent")
@patch("ngRadar_Website.views.views.uiEvent")
def test_get_obs_events(Mock_uiEvent, Mock_dsoc_Event, Mock_gbtEvent, Mock_ObservatoryEvent):

    obs_event_arr = []
    gbt_event_arr = []
    dsoc_event_arr = []
    ui_event_arr = []

    number_in_database = random.randint(RECORDS_TO_DISPLAY, 30) #put random number of items in database
    for i in range(number_in_database+1):
        #generate mock data for use in this test
        mockID_arr=["1","2","3","4","5"]
        mockTarget_arr=["alpha", "bravo", "charlie", "delta", "echo"]
        arrayIndex = random.randint(0,len(mockID_arr)-1)
        #gets mock ID and target from the array
        mockID = mockID_arr[arrayIndex]
        mockTarget = mockTarget_arr[arrayIndex]
        mockWaveform = random.randint(45,55)
        currentDate = datetime.now(timezone.utc)
        mock_latency = random.randint(100, 1000)
        mockUUID = gen_pattern_uuid_like()
        mockBytes = random.randint(100000, 500000)
        mockID = gen_8char_ID()

        #call functions which will produce the objects
        obs_event = getMockObsEvent(mockID, mockTarget, mockWaveform,currentDate,mock_latency)
        gbt_event = getMockGBTEvent(mockID, mockTarget, mockWaveform,currentDate,mock_latency,mockUUID)
        dsoc_event = getMockDSOCEvent(mockID, mockTarget,currentDate,mock_latency,mockUUID, mockBytes)
        ui_event = getMockUIEvent(mockUUID,mockWaveform,currentDate)

        #add the objects to the lists
        obs_event_arr.append(obs_event)
        gbt_event_arr.append(gbt_event)
        dsoc_event_arr.append(dsoc_event)
        ui_event_arr.append(ui_event)

    Mock_ObservatoryEvent.objects.order_by.return_value = MockQuery.MockQuery(obs_event_arr)
    Mock_gbtEvent.objects.order_by.return_value = MockQuery.MockQuery(gbt_event_arr)
    Mock_dsoc_Event.objects.order_by.return_value = MockQuery.MockQuery(dsoc_event_arr)
    Mock_uiEvent.objects.order_by.return_value = MockQuery.MockQuery(ui_event_arr)

    theObservatoryEvents = get_obs_events()

    latest_obs_event = theObservatoryEvents["latest_events"]
    print((latest_obs_event.items()))
    # print(latest_obs_events.list)
    # length = RECORDS_TO_DISPLAY
    # assert len(latest_obs_events) == length


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