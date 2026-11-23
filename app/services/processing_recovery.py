"""Read-only detection of potentially abandoned renders.

A timestamp alone is not a worker lease. Never automatically reset or retry
these records: an FFmpeg worker may still be alive after the threshold.
"""
from datetime import datetime, timedelta, timezone

from ..models import Clip, db


def find_stale_processing_clips(*, now=None, older_than=timedelta(hours=2), limit=100):
    """Return oldest candidate clip IDs for operator investigation, without mutation."""
    if type(older_than) is not timedelta or older_than <= timedelta(0):
        raise ValueError("older_than must be a positive timedelta")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    cutoff = now.astimezone(timezone.utc) - older_than
    rows = (
        db.session.query(Clip.id)
        .filter(
            Clip.editorial_status == "processing",
            Clip.processing_started_at.isnot(None),
            Clip.processing_started_at <= cutoff,
        )
        .order_by(Clip.processing_started_at.asc(), Clip.id.asc())
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]


def find_untracked_processing_clips(*, limit=100):
    """Find processing records lacking a start timestamp (legacy or inconsistent).

    Diagnostic only: never reset, enqueue, or assume that a worker is dead.
    """
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    rows = (
        db.session.query(Clip.id)
        .filter(
            Clip.editorial_status == "processing",
            Clip.processing_started_at.is_(None),
        )
        .order_by(Clip.id.asc())
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]


def summarize_processing_backlog(*, now=None, older_than=timedelta(hours=2),
                                 future_tolerance=timedelta(minutes=5)):
    """Read-only counts for operator dashboards; never claim a worker is dead.

    Counts are deliberately independent of paginated candidate lists, so an
    operator can see the full backlog even when only 100 IDs are displayed.
    """
    if type(older_than) is not timedelta or older_than <= timedelta(0):
        raise ValueError("older_than must be a positive timedelta")
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    cutoff = now.astimezone(timezone.utc) - older_than
    base = db.session.query(Clip.id).filter(Clip.editorial_status == "processing")
    tracked = base.filter(Clip.processing_started_at.isnot(None))
    return {
        "processing_total": base.count(),
        "stale_candidates": tracked.filter(Clip.processing_started_at <= cutoff).count(),
        "untracked_candidates": base.filter(Clip.processing_started_at.is_(None)).count(),
        "recent_or_active": tracked.filter(\n            Clip.processing_started_at > cutoff,\n            Clip.processing_started_at <= future_cutoff,\n        ).count(),\n        "future_clock_skew_candidates": tracked.filter(\n            Clip.processing_started_at > future_cutoff\n        ).count(),
    }


def find_future_processing_clips(*, now=None, tolerance=timedelta(minutes=5), limit=100):
    """Find clock-skewed processing timestamps for manual inspection only."""
    if type(tolerance) is not timedelta or tolerance < timedelta(0):
        raise ValueError("tolerance must be a nonnegative timedelta")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    cutoff = now.astimezone(timezone.utc) + tolerance
    rows = (
        db.session.query(Clip.id)
        .filter(Clip.editorial_status == "processing", Clip.processing_started_at > cutoff)
        .order_by(Clip.processing_started_at.desc(), Clip.id.asc())
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]
