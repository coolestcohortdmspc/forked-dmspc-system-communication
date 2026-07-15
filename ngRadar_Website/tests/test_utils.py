from datetime import datetime, timedelta, timezone
from ngRadar_Website.utils import latency_calc


# ===============================================
# Here we can test all of our utility functions
# ===============================================

# Right now we only have latency_calc, but maybe we will have others here too

def test_latency_calc():
    event_time = datetime.now(timezone.utc) - timedelta(seconds=1)
    latency = latency_calc(event_time)
    
    # 3. Assert (1 second = 1000 milliseconds)
    assert 1000 <= latency < 1100, f"Expected latency around 1000 ms, got {latency} ms"
