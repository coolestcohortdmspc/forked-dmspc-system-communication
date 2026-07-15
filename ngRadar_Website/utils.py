from datetime import datetime, timezone


def latency_calc(event_time):
  #calculates the latency of the message from the time it was sent to the time it was received
  #returns latency in milliseconds

  current_time = datetime.now(timezone.utc)
  latency = current_time - event_time
  latency_ms = latency.total_seconds() * 1000
  return latency_ms