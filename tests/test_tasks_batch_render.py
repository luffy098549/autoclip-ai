"""Regression tests for bounded, non-publishing Celery batch renders."""
from types import SimpleNamespace
import pytest
from flask import Flask

import app
from app.tasks import render_clip_batch_task
from app.services import clip_processor
from app.models import db


@pytest.mark.parametrize("ids", [[], list(range(1, 7)), [1, 1], [0], [-1], [True], ["1"], [1.0], None])
def test_batch_rejects_invalid_ids_before_app_creation(monkeypatch, ids):
    def unexpected():
        raise AssertionError("Should not create an app for invalid IDs")
    monkeypatch.setattr(app, "create_app", unexpected)
    with pytest.raises(ValueError):
        render_clip_batch_task(ids)


@pytest.fixture
def batch_context(monkeypatch):
    monkeypatch.setattr(app, "create_app", lambda: Flask(__name__))
    statuses = {}
    seen = []
    rollbacks = []
    monkeypatch.setattr(db.session, "get", lambda model, clip_id: (
        SimpleNamespace(editorial_status=statuses.get(clip_id, "draft"))
        if statuses.get(clip_id) != "missing" else None
    ))
    monkeypatch.setattr(db.session, "rollback", lambda: rollbacks.append(True))
    return statuses, seen, rollbacks


def test_batch_processes_independently_without_publishing(monkeypatch, batch_context):
    statuses, seen, rollbacks = batch_context

    def process(clip_id):
        seen.append(clip_id)
        if clip_id == 2:
            raise RuntimeError("private media path must not leak")
        return {"status": "ready"}

    monkeypatch.setattr(clip_processor, "process_clip", process)
    result = render_clip_batch_task([1, 2, 3])
    assert seen == [1, 2, 3]
    assert result == {
        "rendered_clip_ids": [1, 3],
        "failed_clip_ids": [2],
        "skipped_clip_ids": [],
    }
    assert len(rollbacks) == 1
    assert "private" not in repr(result)


def test_batch_accepts_single_clip(monkeypatch, batch_context):
    monkeypatch.setattr(clip_processor, "process_clip", lambda clip_id: None)
    assert render_clip_batch_task([7]) == {
        "rendered_clip_ids": [7], "failed_clip_ids": [], "skipped_clip_ids": []
    }


@pytest.mark.parametrize("status", [
    "ready", "rejected", "processing", "approved", "published", "missing",
    "scheduled", "unknown", "rendering"
])
def test_batch_skips_protected_or_missing_clips(monkeypatch, batch_context, status):
    statuses, seen, _ = batch_context
    statuses[2] = status
    monkeypatch.setattr(clip_processor, "process_clip", lambda clip_id: seen.append(clip_id))
    assert render_clip_batch_task([1, 2, 3]) == {
        "rendered_clip_ids": [1, 3], "failed_clip_ids": [], "skipped_clip_ids": [2]
    }
    assert seen == [1, 3]


def test_batch_allows_explicit_retry_of_failed_clips(monkeypatch, batch_context):
    statuses, seen, _ = batch_context
    statuses[2] = "failed"
    monkeypatch.setattr(clip_processor, "process_clip", lambda clip_id: seen.append(clip_id))
    result = render_clip_batch_task([2])
    assert result == {
        "rendered_clip_ids": [2], "failed_clip_ids": [], "skipped_clip_ids": []
    }
    assert seen == [2]


def test_analyze_auto_render_recovers_after_failed_candidate(monkeypatch):
    """A broken DB session from one render must not block the next candidate."""
    from app.tasks import analyze_source_task
    from app.services import analyzer, daily_review, rights
    from app.models import Clip, MediaSource

    flask_app = Flask(__name__)
    flask_app.config["AUTO_RENDER_ENABLED"] = True
    monkeypatch.setattr(app, "create_app", lambda: flask_app)
    monkeypatch.setattr(analyzer, "analyze_source", lambda source_id: {"clip_ids": [1, 2]})
    monkeypatch.setattr(daily_review, "reserve_review_slot", lambda clip_id: clip_id)
    monkeypatch.setattr(rights, "assess_rights", lambda *args: SimpleNamespace(allowed=True))
    clips = {
        1: SimpleNamespace(editorial_status="draft", source_id=10),
        2: SimpleNamespace(editorial_status="failed", source_id=10),
    }
    source = SimpleNamespace(rights_status="owned", permission_evidence="test-owned-media")
    monkeypatch.setattr(db.session, "get", lambda model, identifier: (
        clips.get(identifier) if model is Clip else source if model is MediaSource else None
    ))
    rollbacks = []
    monkeypatch.setattr(db.session, "rollback", lambda: rollbacks.append(True))
    attempts = []

    def process(clip_id):
        attempts.append(clip_id)
        if clip_id == 1:
            raise RuntimeError("internal private path")

    monkeypatch.setattr(clip_processor, "process_clip", process)
    result = analyze_source_task(10)
    assert attempts == [1, 2]
    assert result["rendered_clip_ids"] == [2]
    assert result["failed_clip_ids"] == [1]
    assert rollbacks == [True]
    assert "private" not in repr(result)


@pytest.mark.parametrize("status", ["scheduled", "unknown", "rejected", "processing", "approved", "published"])
def test_analyze_auto_render_skips_non_renderable_states(monkeypatch, status):
    from app.tasks import analyze_source_task
    from app.services import analyzer
    from app.models import Clip

    flask_app = Flask(__name__)
    flask_app.config["AUTO_RENDER_ENABLED"] = True
    monkeypatch.setattr(app, "create_app", lambda: flask_app)
    monkeypatch.setattr(analyzer, "analyze_source", lambda source_id: {"clip_ids": [4]})
    monkeypatch.setattr(db.session, "get", lambda model, identifier: (
        SimpleNamespace(editorial_status=status) if model is Clip else None
    ))
    monkeypatch.setattr(clip_processor, "process_clip",
                        lambda clip_id: pytest.fail("Non-renderable clip processed"))
    result = analyze_source_task(10)
    assert result["rendered_clip_ids"] == []
    assert result["failed_clip_ids"] == []
