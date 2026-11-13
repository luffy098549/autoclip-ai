"""Invalid Celery payloads must fail before initializing Flask or touching data."""
import pytest

from app.tasks import (
    _positive_id,
    render_clip_task,
    analyze_source_task,
    youtube_metadata_task,
)


@pytest.mark.parametrize("invalid", [None, True, False, 0, -1, 1.5, "1", [], {}])
def test_positive_id_rejects_malformed_payload(invalid):
    with pytest.raises(ValueError, match="must be a positive integer"):
        _positive_id(invalid, "clip_id")


@pytest.mark.parametrize("valid", [1, 42, 1000000])
def test_positive_id_accepts_real_ids(valid):
    assert _positive_id(valid, "clip_id") == valid


@pytest.mark.parametrize("task", [
    render_clip_task, analyze_source_task, youtube_metadata_task,
])
@pytest.mark.parametrize("invalid", [0, -5, True, "7", None])
def test_worker_tasks_reject_bad_ids_before_creating_app(monkeypatch, task, invalid):
    import app

    def forbidden_app():
        pytest.fail("Invalid payload must not initialize the application")

    monkeypatch.setattr(app, "create_app", forbidden_app)
    with pytest.raises(ValueError, match="must be a positive integer"):
        task.run(invalid)


def test_analysis_auto_render_deduplicates_candidate_ids(monkeypatch):
    """Duplicate analyzer candidates must not reserve or render twice."""
    from contextlib import nullcontext
    from types import SimpleNamespace
    import app
    from app.models import Clip, MediaSource, db
    from app.services import analyzer, clip_processor, daily_review, rights

    monkeypatch.setattr(app, "create_app", lambda: SimpleNamespace(
        config={"AUTO_RENDER_ENABLED": True},
        app_context=lambda: nullcontext(),
    ))
    monkeypatch.setattr(analyzer, "analyze_source", lambda source_id: {
        "clip_ids": [3, 3, 4, 4],
    })
    clip = SimpleNamespace(source_id=9, editorial_status="pending")
    source = SimpleNamespace(rights_status="owned", permission_evidence="owned")
    monkeypatch.setattr(db.session, "get", lambda model, pk: (
        clip if model is Clip else source if model is MediaSource else None
    ))
    monkeypatch.setattr(rights, "assess_rights", lambda *args: SimpleNamespace(allowed=True))
    reservations = []
    renders = []
    monkeypatch.setattr(daily_review, "reserve_review_slot",
                        lambda pk: reservations.append(pk) or True)
    monkeypatch.setattr(clip_processor, "process_clip",
                        lambda pk: renders.append(pk))
    result = analyze_source_task.run(1)
    assert reservations == [3, 4]
    assert renders == [3, 4]
    assert result["rendered_clip_ids"] == [3, 4]
    assert result["failed_clip_ids"] == []
