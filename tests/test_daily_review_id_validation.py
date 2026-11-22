"""Reject malformed review reservations without touching the database."""
from datetime import datetime, timezone

import pytest

from app.services import daily_review


@pytest.mark.parametrize("clip_id", [
    None, True, False, 0, -1, "1", 1.0, [], {}, 2**63,
])
def test_reservation_rejects_invalid_id_before_database_access(monkeypatch, clip_id):
    def unexpected_database_access(*args, **kwargs):
        raise AssertionError("invalid ID must not query the database")

    monkeypatch.setattr(
        daily_review.db.session, "query", unexpected_database_access
    )
    with pytest.raises(ValueError, match="clip_id"):
        daily_review.reserve_review_slot(clip_id)


def test_reservation_rejects_naive_time_before_database_access(monkeypatch):
    def unexpected_database_access(*args, **kwargs):
        raise AssertionError("naive datetime must not query the database")

    monkeypatch.setattr(
        daily_review.db.session, "query", unexpected_database_access
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        daily_review.reserve_review_slot(1, now=datetime(2026, 11, 22))


def test_reservation_accepts_boundary_database_integer(monkeypatch):
    """A valid maximum ID reaches the query, rather than failing validation."""
    class QueryReached(Exception):
        pass

    def query_reached(*args, **kwargs):
        raise QueryReached

    monkeypatch.setattr(daily_review.db.session, "query", query_reached)
    with pytest.raises(QueryReached):
        daily_review.reserve_review_slot(2**63 - 1, now=datetime.now(timezone.utc))
