"""Reject invalid Celery task identifiers without initializing services."""
import pytest

from app.tasks import (
    analyze_source_task,
    render_clip_task,
    youtube_metadata_task,
)


@pytest.mark.parametrize("task", [
    render_clip_task, analyze_source_task, youtube_metadata_task,
])
@pytest.mark.parametrize("bad_id", [
    None, True, False, 0, -1, 1.5, "1", [], {}, 10**1000,
])
def test_invalid_task_id_rejected_before_app_initialization(task, bad_id, monkeypatch):
    def no_app(*args, **kwargs):
        pytest.fail("Invalid identifier initialized the application")

    monkeypatch.setattr("app.create_app", no_app)
    with pytest.raises(ValueError, match="positive integer"):
        task.run(bad_id)


@pytest.mark.parametrize("task", [
    render_clip_task, analyze_source_task, youtube_metadata_task,
])
def test_positive_task_id_passes_input_validation(task, monkeypatch):
    def sentinel(*args, **kwargs):
        raise RuntimeError("app initialized")

    monkeypatch.setattr("app.create_app", sentinel)
    if task is youtube_metadata_task:
        monkeypatch.setenv("YOUTUBE_API_KEY", "dummy-test-key")
    with pytest.raises(RuntimeError, match="app initialized"):
        task.run(1)
