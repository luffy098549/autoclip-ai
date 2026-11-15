"""Smoke tests for the opt-in dispatch gate and scoring/planning policy."""
from unittest.mock import patch
from flask import Flask
from app.services.auto_dispatch import dispatch_due
from app.intelligence.daily_selection import select_daily_clips
from types import SimpleNamespace


def test_dispatch_disabled_never_queries_database():
    app = Flask(__name__)
    app.config["AUTO_PUBLISH_YOUTUBE_PRIVATE"] = False
    with app.app_context():
        with patch("app.services.auto_dispatch.db") as db:
            assert dispatch_due()["skipped"] is True
            db.session.assert_not_called()


def test_selection_avoids_overlapping_clips():
    clips = [
        SimpleNamespace(id=2, source_id=2, start_seconds=1, end_seconds=30, score=76.6),
        SimpleNamespace(id=3, source_id=2, start_seconds=1, end_seconds=30, score=76.6),
        SimpleNamespace(id=4, source_id=2, start_seconds=1, end_seconds=30, score=76.6),
        SimpleNamespace(id=1, source_id=1, start_seconds=5, end_seconds=20, score=72.1),
    ]
    assert [c.clip_id for c in select_daily_clips(clips)] == [2, 1]
