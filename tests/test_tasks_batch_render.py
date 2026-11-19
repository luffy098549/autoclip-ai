"""Regression tests for bounded, non-publishing Celery batch renders."""
import pytest
from flask import Flask

import app
from app.tasks import render_clip_batch_task
from app.services import clip_processor


@pytest.mark.parametrize("ids", [[], list(range(1, 7)), [1, 1], [0], [-1], [True], ["1"], [1.0], None])
def test_batch_rejects_invalid_ids_before_app_creation(monkeypatch, ids):
    def unexpected():
        raise AssertionError("Should not create an app for invalid IDs")
    monkeypatch.setattr(app, "create_app", unexpected)
    with pytest.raises(ValueError):
        render_clip_batch_task(ids)


def test_batch_processes_independently_without_publishing(monkeypatch):
    monkeypatch.setattr(app, "create_app", lambda: Flask(__name__))
    seen = []

    def process(clip_id):
        seen.append(clip_id)
        if clip_id == 2:
            raise RuntimeError("private media path must not leak")
        return {"status": "ready"}

    monkeypatch.setattr(clip_processor, "process_clip", process)
    result = render_clip_batch_task([1, 2, 3])
    assert seen == [1, 2, 3]
    assert result == {"rendered_clip_ids": [1, 3], "failed_clip_ids": [2]}
    assert "private" not in repr(result)


def test_batch_accepts_single_clip(monkeypatch):
    monkeypatch.setattr(app, "create_app", lambda: Flask(__name__))
    monkeypatch.setattr(clip_processor, "process_clip", lambda clip_id: None)
    assert render_clip_batch_task([7]) == {
        "rendered_clip_ids": [7], "failed_clip_ids": []
    }
