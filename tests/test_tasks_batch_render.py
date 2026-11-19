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
