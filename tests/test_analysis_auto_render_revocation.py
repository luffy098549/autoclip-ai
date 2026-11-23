"""Auto-render analysis must distinguish revoked rights from encoder errors."""
from types import SimpleNamespace

from flask import Flask

from app.tasks import analyze_source_task


def test_analysis_auto_render_continues_after_revocation(monkeypatch):
    from app import models
    from app.services import analyzer, clip_processor, daily_review, rights

    app = Flask(__name__)
    app.config["AUTO_RENDER_ENABLED"] = True
    monkeypatch.setattr("app.create_app", lambda: app)
    monkeypatch.setattr(analyzer, "analyze_source", lambda _: {"clip_ids": [1, 2, 3, 4]})
    clips = {
        i: SimpleNamespace(id=i, source_id=i, editorial_status="queued")
        for i in (1, 2, 3, 4)
    }
    sources = {
        i: SimpleNamespace(id=i, rights_status="authorized", permission_evidence="test")
        for i in (1, 2, 3, 4)
    }
    sources[3].rights_status = "revoked"
    monkeypatch.setattr(
        models.db.session,
        "get",
        lambda model, item_id: clips.get(item_id) if model is models.Clip else sources.get(item_id),
    )
    monkeypatch.setattr(
        rights, "assess_rights",
        lambda status, evidence: SimpleNamespace(allowed=status == "authorized"),
    )
    monkeypatch.setattr(daily_review, "reserve_review_slot", lambda _: object())

    attempted = []

    def render(clip_id):
        attempted.append(clip_id)
        if clip_id == 1:
            raise clip_processor.SourceAuthorizationRevoked("revoked during render")
        if clip_id == 2:
            raise RuntimeError("encoder failed")
        return {"path": "rendered.mp4"}

    monkeypatch.setattr(clip_processor, "process_clip", render)
    result = analyze_source_task.run(10)
    assert attempted == [1, 2, 4]
    assert result["unauthorized_clip_ids"] == [1, 3]
    assert result["failed_clip_ids"] == [2]
    assert result["rendered_clip_ids"] == [4]
