from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.scheduler import can_schedule

TZ = ZoneInfo("America/New_York")

def test_two_hour_spacing():
    start = datetime(2026, 11, 9, 10, tzinfo=TZ)
    assert not can_schedule(start + timedelta(minutes=119), [start])
    assert can_schedule(start + timedelta(minutes=120), [start])

def test_five_posts_cap():
    start = datetime(2026, 11, 9, 8, tzinfo=TZ)
    prior = [start + timedelta(hours=2*i) for i in range(5)]
    assert not can_schedule(start + timedelta(hours=10), prior)

def test_previous_day_interval():
    last = datetime(2026, 11, 9, 23, tzinfo=TZ)
    candidate = datetime(2026, 11, 10, 0, tzinfo=TZ)
    assert not can_schedule(candidate, [last])
