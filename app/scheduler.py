from datetime import timedelta
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/New_York")
MIN_INTERVAL = timedelta(minutes=120)
MAX_PER_DAY = 5
PLATFORMS = ("youtube", "tiktok", "instagram")


def can_schedule(candidate, existing_times):
    """Assumes timezone-aware datetimes and per-platform published/reserved slots."""
    if candidate.tzinfo is None or any(t.tzinfo is None for t in existing_times):
        raise ValueError("Timezone-aware datetimes required")
    local_date = candidate.astimezone(TIMEZONE).date()
    same_day = [t for t in existing_times if t.astimezone(TIMEZONE).date() == local_date]
    if len(same_day) >= MAX_PER_DAY:
        return False
    return all(abs((candidate - t).total_seconds()) >= MIN_INTERVAL.total_seconds() for t in existing_times)
