"""Stale render diagnostics must never mutate a clip or start a worker."""
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.models import Clip, MediaSource, db
from app.services.processing_recovery import find_stale_processing_clips


@pytest.fixture
def recovery_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        try:
            yield app
        finally:
            db.session.remove()
            db.drop_all()


def test_only_old_processing_clips_are_reported_without_mutation(recovery_app):
    now = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)
    with recovery_app.app_context():
        source = MediaSource(source_uri="owned.mp4", rights_status="owned")
        db.session.add(source)
        db.session.flush()
        rows = [
            Clip(source_id=source.id, start_seconds=0, end_seconds=10,
                 editorial_status=status, processing_started_at=stamp)
            for status, stamp in [
                ("processing", now - timedelta(hours=4)),
                ("processing", now - timedelta(hours=3)),
                ("processing", now - timedelta(minutes=10)),
                ("ready", now - timedelta(hours=5)),
                ("processing", None),
            ]
        ]
        db.session.add_all(rows)
        db.session.commit()
        assert find_stale_processing_clips(now=now, limit=1) == [rows[0].id]
        assert find_stale_processing_clips(now=now) == [rows[0].id, rows[1].id]
        db.session.expire_all()
        assert [db.session.get(Clip, row.id).editorial_status for row in rows] == [
            "processing", "processing", "processing", "ready", "processing"
        ]


@pytest.mark.parametrize("kwargs", [
    {"older_than": timedelta(0)},
    {"older_than": timedelta(seconds=-1)},
    {"older_than": 3600},
    {"limit": 0},
    {"limit": True},
    {"limit": 1001},
    {"now": datetime(2026, 11, 22)},
    {"now": "2026-11-22"},
])
def test_invalid_scan_inputs_are_rejected(recovery_app, kwargs):
    with recovery_app.app_context(), pytest.raises(ValueError):
        find_stale_processing_clips(**kwargs)
