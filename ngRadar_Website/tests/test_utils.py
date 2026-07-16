from datetime import datetime, timedelta, timezone
from ngRadar_Website.utils import latency_calc
import pytest


# ===============================================
# Here we can test all of our utility functions
# ===============================================

#can add as many different latency test values here as you want:
testcases = [
    (datetime.now(timezone.utc) - timedelta(seconds=1), 1000),
    (datetime.now(timezone.utc) - timedelta(seconds=2), 2000),
]

@pytest.mark.parametrize("event_time,expected", testcases)
def test_latency_calc(event_time, expected):
    latency = latency_calc(event_time)

    upper_bound = expected+100
    
    # 3. Assert (1 second = 1000 milliseconds)
    assert expected <= latency < upper_bound, f"Expected latency around 1000 ms, got {latency} ms"
