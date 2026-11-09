"""Atomically reserve a daily manual-review slot before rendering.

The unique constraints in the database arbitrate concurrent workers.
Reservations remain allocated after rendering failures to prevent retry storms.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from app.models import db, DailyReviewSlot

REVIEW_TIMEZONE = ZoneInfo("America/New_York")
DAILY_LIMIT = 5


def reserve_review_slot(clip_id: int, now: datetime | None = None) -> int | None:
    """Return reserved slot 1..5, or None when the day is full.

    Caller must have verified clip/source authorization. This function commits
    the reservation independently of later video processing.
    """
    if clip_id <= 0:
        raise ValueError("clip_id must be positive")
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    day = instant.astimezone(REVIEW_TIMEZONE).date()
    for slot in range(1, DAILY_LIMIT + 1):
        existing = db.session.query(DailyReviewSlot).filter_by(clip_id=clip_id).first()
        if existing is not None:
            return existing.slot if existing.review_date == day else None
        try:
            with db.session.begin_nested():
                db.session.add(DailyReviewSlot(review_date=day, slot=slot, clip_id=clip_id))
                db.session.flush()
            db.session.commit()
            return slot
        except IntegrityError:
            db.session.rollback()
            # Another worker may have claimed this slot or this clip.
            continue
    return None
