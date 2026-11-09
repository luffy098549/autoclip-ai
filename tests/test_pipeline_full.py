"""Regression checks for the authorized local video pipeline CLI.

These tests use fakes; actual FFmpeg rendering is exercised by the separate
ffmpeg-end-to-end CI job with synthetic media.
"""
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts import pipeline_full


@pytest.mark.parametrize("value", ["0", "-1"])
def test_rejects_invalid_source_id_before_starting_pipeline(value):
    with patch.object(sys, "argv", ["pipeline_full", value]):
        with patch.object(pipeline_full, "create_app") as app:
            with pytest.raises(SystemExit) as error:
                pipeline_full.main()
            assert error.value.code == 2
            app.assert_not_called()


@pytest.mark.parametrize("value", ["0", "6", "-1"])
def test_rejects_invalid_clip_quota_before_starting_pipeline(value):
    with patch.object(sys, "argv", ["pipeline_full", "1", "--max-clips", value]):
        with patch.object(pipeline_full, "create_app") as app:
            with pytest.raises(SystemExit) as error:
                pipeline_full.main()
            assert error.value.code == 2
            app.assert_not_called()


def test_processes_multiple_clips_and_continues_after_single_failure(capsys):
    clips = {1: SimpleNamespace(editorial_status="pending"),
             2: SimpleNamespace(editorial_status="pending"),
             3: SimpleNamespace(editorial_status="ready")}
    fake_app = SimpleNamespace(app_context=lambda: _Context())

    def render(clip_id):
        if clip_id == 1:
            raise RuntimeError("synthetic FFmpeg failure")
        return {"path": "synthetic-output.mp4"}

    with (patch.object(sys, "argv", ["pipeline_full", "42", "--max-clips", "3"]),
          patch.object(pipeline_full, "create_app", return_value=fake_app) as create,
          patch.object(pipeline_full, "analyze_source", return_value={
              "transcript_segments": 12, "candidate_count": 3, "clip_ids": [1, 2, 3]
          }) as analyze,
          patch.object(pipeline_full.db.session, "get", side_effect=lambda model, clip_id: clips[clip_id]),
          patch.object(pipeline_full.db.session, "rollback") as rollback,
          patch.object(pipeline_full, "process_clip", side_effect=render) as process):
        with pytest.raises(SystemExit) as error:
            pipeline_full.main()
        assert error.value.code == 1
    rollback.assert_called_once_with()
    create.assert_called_once_with({"AUTO_CAPTION_ENABLED": False})
    analyze.assert_called_once_with(42, model_size="small", max_clips=3)
    assert [call.args[0] for call in process.call_args_list] == [1, 2]
    output = capsys.readouterr().out
    assert "Clip 1 failed: RuntimeError" in output
    assert "Rendered clip: 2 synthetic-output.mp4" in output
    assert "Already rendered: 3" in output
    assert "Pipeline summary: rendered=1, already_ready=1, failed=1" in output
    assert "Review every exported clip" in output


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_missing_clip_does_not_prevent_rendering_other_candidates(capsys):
    clips = {2: SimpleNamespace(editorial_status="pending")}
    fake_app = SimpleNamespace(app_context=lambda: _Context())
    with (patch.object(sys, "argv", ["pipeline_full", "42", "--max-clips", "2"]),
          patch.object(pipeline_full, "create_app", return_value=fake_app),
          patch.object(pipeline_full, "analyze_source", return_value={
              "transcript_segments": 2, "candidate_count": 2, "clip_ids": [1, 2]
          }),
          patch.object(pipeline_full.db.session, "get", side_effect=lambda model, clip_id: clips.get(clip_id)),
          patch.object(pipeline_full, "process_clip", return_value={"path": "clip-2.mp4"}) as process):
        with pytest.raises(SystemExit) as error:
            pipeline_full.main()
        assert error.value.code == 1
    process.assert_called_once_with(2)
    output = capsys.readouterr().out
    assert "Clip 1 failed: not found" in output
    assert "Pipeline summary: rendered=1, already_ready=0, failed=1" in output


def test_clip_lookup_error_does_not_stop_other_renders(capsys):
    fake_app = SimpleNamespace(app_context=lambda: _Context())

    def lookup(model, clip_id):
        if clip_id == 1:
            raise RuntimeError("synthetic database lookup failure")
        return SimpleNamespace(editorial_status="pending")

    with (patch.object(sys, "argv", ["pipeline_full", "42", "--max-clips", "2"]),
          patch.object(pipeline_full, "create_app", return_value=fake_app),
          patch.object(pipeline_full, "analyze_source", return_value={
              "transcript_segments": 2, "candidate_count": 2, "clip_ids": [1, 2]
          }),
          patch.object(pipeline_full.db.session, "get", side_effect=lookup),
          patch.object(pipeline_full.db.session, "rollback") as rollback,
          patch.object(pipeline_full, "process_clip", return_value={"path": "clip-2.mp4"}) as process):
        with pytest.raises(SystemExit) as error:
            pipeline_full.main()
        assert error.value.code == 1
    rollback.assert_called_once_with()
    process.assert_called_once_with(2)
    output = capsys.readouterr().out
    assert "Clip 1 failed: RuntimeError" in output
    assert "Rendered clip: 2 clip-2.mp4" in output
    assert "Pipeline summary: rendered=1, already_ready=0, failed=1" in output
