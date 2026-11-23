"""Stale render diagnostics must never mutate a clip or start a worker."""
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.models import Clip, MediaSource, db
from app.services.processing_recovery import find_stale_processing_clips, find_untracked_processing_clips


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


def test_untracked_processing_clips_are_reported_read_only(recovery_app):
    with recovery_app.app_context():
        source = MediaSource(source_uri="owned.mp4", rights_status="owned")
        db.session.add(source)
        db.session.flush()
        rows = [
            Clip(source_id=source.id, start_seconds=0, end_seconds=10,
                 editorial_status=status, processing_started_at=stamp)
            for status, stamp in [
                ("processing", None),
                ("ready", None),
                ("processing", datetime(2026, 11, 22, tzinfo=timezone.utc)),
                ("processing", None),
            ]
        ]
        db.session.add_all(rows)
        db.session.commit()
        assert find_untracked_processing_clips(limit=1) == [rows[0].id]
        assert find_untracked_processing_clips() == [rows[0].id, rows[3].id]
        db.session.expire_all()
        assert [db.session.get(Clip, row.id).editorial_status for row in rows] == [
            "processing", "ready", "processing", "processing"
        ]


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, "10", 1001])
def test_untracked_scan_rejects_invalid_limits(recovery_app, limit):
    with recovery_app.app_context(), pytest.raises(ValueError):
        find_untracked_processing_clips(limit=limit)


def test_backlog_summary_counts_all_categories_without_writes(recovery_app):
    from app.services.processing_recovery import summarize_processing_backlog

    now = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
    with recovery_app.app_context():
        source = MediaSource(source_uri="owned-summary.mp4", rights_status="owned")
        db.session.add(source)
        db.session.flush()
        cases = [
            ("processing", now - timedelta(hours=4)),
            ("processing", now - timedelta(hours=2)),
            ("processing", now - timedelta(minutes=20)),
            ("processing", None),
            ("ready", now - timedelta(days=1)),
        ]
        clips = [
            Clip(source_id=source.id, start_seconds=i * 10,
                 end_seconds=(i + 1) * 10, editorial_status=status,
                 processing_started_at=stamp)
            for i, (status, stamp) in enumerate(cases)
        ]
        db.session.add_all(clips)
        db.session.commit()
        assert summarize_processing_backlog(now=now) == {
            "processing_total": 4,
            "stale_candidates": 2,
            "untracked_candidates": 1,
            "recent_or_active": 1,
        }
        assert not db.session.dirty
        db.session.expire_all()
        assert [db.session.get(Clip, c.id).editorial_status for c in clips] == [
            case[0] for case in cases
        ]


@pytest.mark.parametrize("kwargs", [
    {"older_than": timedelta(0)},
    {"older_than": timedelta(seconds=-1)},
    {"older_than": 1},
    {"now": datetime(2026, 11, 23)},
    {"now": "2026-11-23"},
])
def test_backlog_summary_rejects_invalid_inputs(recovery_app, kwargs):
    from app.services.processing_recovery import summarize_processing_backlog

    with recovery_app.app_context(), pytest.raises(ValueError):
        summarize_processing_backlog(**kwargs)


def test_future_processing_claims_are_diagnostic_only(recovery_app):
    from app.services.processing_recovery import find_future_processing_clips

    now = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
    with recovery_app.app_context():
        source = MediaSource(source_uri="owned-clock-skew.mp4", rights_status="owned")
        db.session.add(source)
        db.session.flush()
        cases = [
            ("processing", now + timedelta(hours=2)),
            ("processing", now + timedelta(minutes=6)),
            ("processing", now + timedelta(minutes=5)),
            ("processing", now - timedelta(minutes=1)),
            ("ready", now + timedelta(days=1)),
        ]
        clips = [Clip(source_id=source.id, start_seconds=i * 10,
                      end_seconds=(i + 1) * 10, editorial_status=status,
                      processing_started_at=stamp)
                 for i, (status, stamp) in enumerate(cases)]
        db.session.add_all(clips)
        db.session.commit()
        assert find_future_processing_clips(now=now) == [clips[0].id, clips[1].id]
        assert find_future_processing_clips(now=now, limit=1) == [clips[0].id]
        assert not db.session.dirty
        db.session.expire_all()
        assert [db.session.get(Clip, clip.id).editorial_status for clip in clips] == [
            status for status, _ in cases
        ]


@pytest.mark.parametrize("kwargs", [
    {"tolerance": timedelta(seconds=-1)},
    {"tolerance": 300},
    {"limit": 0},
    {"limit": True},
    {"limit": 1001},
    {"now": datetime(2026, 11, 23)},
    {"now": "2026-11-23"},
])
def test_future_processing_scan_rejects_invalid_inputs(recovery_app, kwargs):
    from app.services.processing_recovery import find_future_processing_clips

    with recovery_app.app_context(), pytest.raises(ValueError):
        find_future_processing_clips(**kwargs)
