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


@pytest.mark.parametrize("start,end,source_duration", [
    (0, 301, 400), (10, 9, 400), (0, 21, 20), (float("nan"), 5, 400),
])
def test_pipeline_rejects_invalid_ranges_before_render(tmp_path, start, end, source_duration):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"synthetic fixture")
    target = tmp_path / "clip.mp4"
    with patch("app.pipeline.inspect_video", return_value={
        "duration": source_duration, "has_audio": True, "width": 320, "height": 180,
    }), patch("app.pipeline.render_vertical_clip") as render:
        with pytest.raises(ValueError):
            create_local_clip(source, target, start=start, end=end, authorized=True)
        render.assert_not_called()


def test_pipeline_passes_validated_bounds_to_renderer(tmp_path):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"synthetic fixture")
    target = tmp_path / "clip.mp4"
    info = {"duration": 30, "has_audio": True, "width": 320, "height": 180}
    with patch("app.pipeline.inspect_video", return_value=info), \
         patch("app.pipeline.render_vertical_clip", return_value=target) as render, \
         patch("app.pipeline.validate_render", return_value=info):
        result = create_local_clip(source, target, start=2, end=12, authorized=True)
    render.assert_called_once_with(source, target, 2.0, 12.0)
    assert result["path"] == target


def test_pipeline_allows_clip_longer_than_twenty_seconds_when_source_supports_it(tmp_path):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"synthetic fixture")
    target = tmp_path / "clip.mp4"
    info = {"duration": 400, "has_audio": True, "width": 320, "height": 180}
    with patch("app.pipeline.inspect_video", return_value=info), \
         patch("app.pipeline.render_vertical_clip", return_value=target) as render, \
         patch("app.pipeline.validate_render", return_value=info):
        create_local_clip(source, target, start=0, end=21, authorized=True)
    render.assert_called_once_with(source, target, 0.0, 21.0)
