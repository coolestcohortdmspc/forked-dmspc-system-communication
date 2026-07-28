from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from ngRadar_Website.views.views import get_Message_Latency

import json

#set number of valid events
NUMBEROFEVENTS = 5

class SimulatedEvent:
    def __init__(self, object_id, target, tx_waveform, event_time, latency_ms):
        self.object_id = object_id
        self.target = target
        self.tx_waveform = tx_waveform
        self.event_time = event_time
        self.latency_ms = latency_ms
    def getEventLatency(self):
        return self.latency_ms
    def getEventTime(self):
        return self.event_time
        
@patch("ngRadar_Website.views.views.ObservatoryEvent")
def test_get_Message_Latency(Mock_ObservatoryEvent):
        
    mock_event_time1=datetime(2026, 7, 20, 12, 30, 28, tzinfo=timezone.utc)
    print(mock_event_time1)
    mock_event_time2=datetime(2026, 7, 20, 13, 10, 15, tzinfo=timezone.utc)
    mock_event_time3=datetime(2026, 7, 20, 13, 20, 43, tzinfo=timezone.utc)
    mock_event_time4=datetime(2026, 7, 20, 14, 10, 10, tzinfo=timezone.utc)
    mock_event_time5=datetime(2026, 7, 20, 14, 42, 34, tzinfo=timezone.utc)
    mock_event_time6=datetime(2026, 7, 20, 15, 15, 18, tzinfo=timezone.utc)

    simulated_event_1 = SimulatedEvent(object_id="1", target="alpha", tx_waveform="45", event_time=mock_event_time1, latency_ms=500)
    simulated_event_2 = SimulatedEvent(object_id="2", target="bravo", tx_waveform="46", event_time=mock_event_time2, latency_ms=250)
    simulated_event_3 = SimulatedEvent(object_id="3", target="charlie", tx_waveform="47", event_time=mock_event_time3, latency_ms=300)
    simulated_event_4 = SimulatedEvent(object_id="4", target="delta", tx_waveform="48", event_time=mock_event_time4, latency_ms=1200)
    simulated_event_5 = SimulatedEvent(object_id="5", target="echo", tx_waveform="49", event_time=mock_event_time5, latency_ms=800)
    simulated_event_6 = SimulatedEvent(object_id="6", target="foxtrot", tx_waveform="Tx_OFF", event_time=mock_event_time6, latency_ms=650)

    sim_obs_event_arr = [simulated_event_1,simulated_event_2,simulated_event_3,simulated_event_4,simulated_event_5,simulated_event_6]

    Mock_ObservatoryEvent.objects.order_by.return_value = sim_obs_event_arr

    mockGeneratorData = get_Message_Latency()

    mockList = list(mockGeneratorData) #convert this to a list object - originally returns as generator

    removeLen = len("data:") #get how many digits to remove
    payload = mockList[0][removeLen:] #removes the word "data:" from the list
    payload = payload.strip() #removes extra whitespace. Necessary to convert to JSON

    mockJSONData = json.loads(payload) #convert the payload into a JSON message

    latency_array = mockJSONData["latency_array"]
    time_sent_array = mockJSONData["time_sent_array"]

    print("Does Number of Elements in the Latency Array Equal the Number of Events?")
    assert len(latency_array) == NUMBEROFEVENTS

    print("Does Number of Elements in the Time Sent Array Equal the Number of Events?")
    assert len(time_sent_array) == NUMBEROFEVENTS

    print("Are all the elements in the Latency Array Numbers?")
    for time in latency_array:
        if(isinstance(time,str)):
            t = float(time.strip()) #remove whitespace and attempt to convert to float
            isInt_or_Float = False
            assert (isinstance(t,float)) == True
    
    print("Does the last element in the mock database match most recent latency and time")
    assert (float(latency_array[NUMBEROFEVENTS-1])) == float(simulated_event_5.getEventLatency())
    
    outputTimeStr = "".join(time_sent_array[NUMBEROFEVENTS-1]) #combine the list into one string
    originalTimeStr = str(simulated_event_5.getEventTime()) #convert the last date time into a string 
    formatted_time_str = (originalTimeStr[0:10]+originalTimeStr[11:19])#format the time 
    assert (outputTimeStr == formatted_time_str)