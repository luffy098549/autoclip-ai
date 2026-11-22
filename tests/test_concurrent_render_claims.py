"""Concurrent claims are skips, not failed renders, in both worker paths."""
from types import SimpleNamespace

from flask import Flask

from app.tasks import analyze_source_task, render_clip_batch_task


def _setup(monkeypatch):
    from app import models
    from app.services import rights, clip_processor
    app = Flask(__name__)
    app.config["AUTO_RENDER_ENABLED"] = True
    monkeypatch.setattr("app.create_app", lambda: app)
    clips = {i: SimpleNamespace(id=i, source_id=10, editorial_status="queued") for i in (1, 2)}
    source = SimpleNamespace(id=10, rights_status="authorized", permission_evidence="test")
    monkeypatch.setattr(
        models.db.session, "get",
        lambda model, item_id: clips.get(item_id) if model is models.Clip else source,
    )
    monkeypatch.setattr(rights, "assess_rights", lambda *args: SimpleNamespace(allowed=True))
    from app.services import daily_review
    monkeypatch.setattr(daily_review, "reserve_review_slot", lambda clip_id: clip_id)
    attempts = []

    def render(clip_id):
        attempts.append(clip_id)
        if clip_id == 1:
            raise clip_processor.ClipNotEligibleError("claimed by another worker")
        return {"path": "clip-2.mp4"}

    monkeypatch.setattr(clip_processor, "process_clip", render)
    return attempts


def test_batch_concurrent_claim_skips_and_continues(monkeypatch):
    attempts = _setup(monkeypatch)
    result = render_clip_batch_task.run([1, 2])
    assert attempts == [1, 2]
    assert result["skipped_clip_ids"] == [1]
    assert result["rendered_clip_ids"] == [2]
    assert result["failed_clip_ids"] == []
    assert result["unauthorized_clip_ids"] == []


def test_analysis_concurrent_claim_skips_and_continues(monkeypatch):
    from app.services import analyzer, daily_review
    attempts = _setup(monkeypatch)
    monkeypatch.setattr(analyzer, "analyze_source", lambda _: {"clip_ids": [1, 2]})
    monkeypatch.setattr(daily_review, "reserve_review_slot", lambda _: object())
    result = analyze_source_task.run(10)
    assert attempts == [1, 2]
    assert result["skipped_clip_ids"] == [1]
    assert result["rendered_clip_ids"] == [2]
    assert result["failed_clip_ids"] == []
    assert result["unauthorized_clip_ids"] == []
