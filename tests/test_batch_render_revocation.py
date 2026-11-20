"""Batch rendering must report revocations separately from encoder failures."""
from types import SimpleNamespace

import pytest
from flask import Flask

from app.tasks import render_clip_batch_task


@pytest.mark.parametrize(
    ("outcome", "expected_key"),
    [
        ("revoked", "unauthorized_clip_ids"),
        ("encoder_failure", "failed_clip_ids"),
        ("success", "rendered_clip_ids"),
    ],
)
def test_batch_render_reports_outcome_and_continues(monkeypatch, outcome, expected_key):
    from app import models
    from app.services import clip_processor, rights

    app = Flask(__name__)
    monkeypatch.setattr("app.create_app", lambda: app)

    clips = {
        1: SimpleNamespace(id=1, source_id=10, editorial_status="queued"),
        2: SimpleNamespace(id=2, source_id=10, editorial_status="queued"),
    }
    source = SimpleNamespace(id=10, rights_status="authorized", permission_evidence="test")
    monkeypatch.setattr(
        models.db.session,
        "get",
        lambda model, item_id: clips.get(item_id) if model is models.Clip else source,
    )
    monkeypatch.setattr(rights, "assess_rights", lambda *args: SimpleNamespace(allowed=True))

    processed = []

    def process(clip_id):
        processed.append(clip_id)
        if clip_id == 1 and outcome == "revoked":
            raise PermissionError("authorization revoked during rendering")
        if clip_id == 1 and outcome == "encoder_failure":
            raise RuntimeError("encoder failed")
        return {"path": f"clip-{clip_id}.mp4"}

    monkeypatch.setattr(clip_processor, "process_clip", process)
    result = render_clip_batch_task.run([1, 2])

    assert processed == [1, 2]
    assert result[expected_key] == ([1] if outcome != "success" else [1, 2])
    assert result["rendered_clip_ids"] == ([1, 2] if outcome == "success" else [2])
    assert result["failed_clip_ids"] == ([1] if outcome == "encoder_failure" else [])
    assert result["unauthorized_clip_ids"] == ([1] if outcome == "revoked" else [])
    assert result["skipped_clip_ids"] == []
