"""Concurrency regression tests: pipeline never deletes another worker's output."""
from unittest.mock import patch

import pytest

from app.pipeline import create_local_clip


def test_competing_export_survives_render_failure(tmp_path):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"synthetic fixture")
    target = tmp_path / "clip.mp4"

    def competing_worker(_source, destination, _start, _end):
        destination.write_bytes(b"other worker export")
        raise FileExistsError("another worker published first")

    with patch("app.pipeline.inspect_video", return_value={
        "duration": 20, "has_audio": True, "width": 320, "height": 180,
    }), patch("app.pipeline.render_vertical_clip", side_effect=competing_worker):
        with pytest.raises(FileExistsError):
            create_local_clip(source, target, start=0, end=5, authorized=True)

    assert target.read_bytes() == b"other worker export"


def test_render_failure_does_not_remove_preexisting_symlink(tmp_path):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"synthetic fixture")
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"protected")
    target = tmp_path / "clip.mp4"
    target.symlink_to(outside)

    with pytest.raises(FileExistsError):
        create_local_clip(source, target, start=0, end=5, authorized=True)

    assert target.is_symlink()
    assert outside.read_bytes() == b"protected"


def test_rights_check_precedes_media_probe(tmp_path):
    with patch("app.pipeline.inspect_video") as probe:
        with pytest.raises(PermissionError):
            create_local_clip(tmp_path / "unknown.mp4", tmp_path / "clip.mp4",
                              start=0, end=5, authorized=False)
        probe.assert_not_called()
