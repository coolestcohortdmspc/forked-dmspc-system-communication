from ngRadar_Website.utils import latency_calc
from datetime import datetime, timedelta, timezone


def test_latency_calc():
    # Test with a known event time
    event_time = datetime.now(timezone.utc) - timedelta(seconds=1)  # 1 second ago
    latency = latency_calc(event_time)
    assert 1000 <= latency < 1100, f"Expected latency around 1000 ms, got {latency} ms"