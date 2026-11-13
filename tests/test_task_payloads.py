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
