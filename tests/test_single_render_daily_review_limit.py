"""Single clip workers must not bypass the manual review quota or rights checks."""
from types import SimpleNamespace

import pytest
from flask import Flask

import app
from app.models import Clip, MediaSource, db
from app.services import clip_processor, daily_review
from app.tasks import render_clip_task


@pytest.mark.parametrize("clip_status,rights,expected", [
    ("draft", "owned", "rendered"),
    ("awaiting_worker", "owned", "rendered"),
    ("ready", "owned", "skipped"),
    ("draft", "unverified", "unauthorized"),
])
def test_single_render_preflight(monkeypatch, clip_status, rights, expected):
    monkeypatch.setattr(app, "create_app", lambda: Flask(__name__))
    source = SimpleNamespace(rights_status=rights, permission_evidence="original operator footage" if rights == "owned" else None)
    monkeypatch.setattr(db.session, "get", lambda model, identifier: (
        SimpleNamespace(editorial_status=clip_status, source_id=12) if model is Clip
        else source if model is MediaSource else None
    ))
    reserved = []
    monkeypatch.setattr(daily_review, "reserve_review_slot", lambda clip_id: reserved.append(clip_id) or 1)
    rendered = []
    monkeypatch.setattr(clip_processor, "process_clip", lambda clip_id: rendered.append(clip_id) or {"status": "ready"})
    result = render_clip_task.run(7)
    assert rendered == ([7] if expected == "rendered" else [])
    assert reserved == ([7] if expected == "rendered" else [])
    assert result == ({"status": "ready"} if expected == "rendered" else {"status": expected, "clip_id": 7})


def test_single_render_defers_when_budget_exhausted(monkeypatch):
    monkeypatch.setattr(app, "create_app", lambda: Flask(__name__))
    monkeypatch.setattr(db.session, "get", lambda model, identifier: (
        SimpleNamespace(editorial_status="draft", source_id=12) if model is Clip
        else SimpleNamespace(rights_status="owned", permission_evidence="original footage")
    ))
    monkeypatch.setattr(daily_review, "reserve_review_slot", lambda clip_id: None)
    monkeypatch.setattr(clip_processor, "process_clip", lambda clip_id: pytest.fail("quota bypass"))
    assert render_clip_task.run(7) == {"status": "deferred", "clip_id": 7}


@pytest.mark.parametrize("invalid", [0, -1, True, "7", 7.0, 2**63])
def test_single_render_rejects_invalid_id_without_app(monkeypatch, invalid):
    monkeypatch.setattr(app, "create_app", lambda: pytest.fail("invalid ID reached app"))
    with pytest.raises(ValueError):
        render_clip_task.run(invalid)


@pytest.mark.parametrize("error_name,expected_status", [
    ("ClipNotEligibleError", "skipped"),
    ("SourceAuthorizationRevoked", "unauthorized"),
])
def test_single_render_handles_race_or_revocation(monkeypatch, error_name, expected_status):
    monkeypatch.setattr(app, "create_app", lambda: Flask(__name__))
    monkeypatch.setattr(db.session, "get", lambda model, identifier: (
        SimpleNamespace(editorial_status="draft", source_id=12) if model is Clip
        else SimpleNamespace(rights_status="owned", permission_evidence="original footage")
    ))
    monkeypatch.setattr(daily_review, "reserve_review_slot", lambda clip_id: 1)
    from app.services.clip_processor import ClipNotEligibleError, SourceAuthorizationRevoked
    error_type = {
        "ClipNotEligibleError": ClipNotEligibleError,
        "SourceAuthorizationRevoked": SourceAuthorizationRevoked,
    }[error_name]
    def raise_error(_clip_id):
        raise error_type("worker preflight changed")
    monkeypatch.setattr(clip_processor, "process_clip", raise_error)
    rolled_back = []
    monkeypatch.setattr(db.session, "rollback", lambda: rolled_back.append(True))
    assert render_clip_task.run(7) == {"status": expected_status, "clip_id": 7}
    assert rolled_back == [True]
