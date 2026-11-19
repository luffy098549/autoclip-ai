"""Tests for local-only metadata inspection using synthetic inputs."""
import json
import shutil
import subprocess
from unittest.mock import patch

import pytest
from app.media_probe import inspect_local_video, validate_clip_range


def test_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        inspect_local_video(tmp_path / "missing.mp4")


def test_reject_audio_only(tmp_path):
    source = tmp_path / "audio.mp4"
    source.write_bytes(b"fixture")
    with patch("app.media_probe.subprocess.run") as run:
        run.return_value.stdout = json.dumps({"streams": [{"codec_type": "audio"}], "format": {"duration": "2"}})
        with pytest.raises(ValueError, match="no video"):
            inspect_local_video(source)


@pytest.mark.parametrize("duration,width,height", [("nan", 320, 180), ("0", 320, 180), ("2", 0, 180)])
def test_reject_invalid_metadata(tmp_path, duration, width, height):
    source = tmp_path / "invalid.mp4"
    source.write_bytes(b"fixture")
    with patch("app.media_probe.subprocess.run") as run:
        run.return_value.stdout = json.dumps({"streams": [{"codec_type": "video", "width": width, "height": height}], "format": {"duration": duration}})
        with pytest.raises(ValueError, match="Invalid video"):
            inspect_local_video(source)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools unavailable")
def test_real_synthetic_video(tmp_path):
    source = tmp_path / "synthetic.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=12:d=1", "-an", "-c:v", "mpeg4", str(source)], check=True, timeout=30)
    metadata = inspect_local_video(source)
    assert metadata["width"] == 320
    assert metadata["height"] == 180
    assert metadata["duration_seconds"] > 0
    assert metadata["has_audio"] is False


@pytest.mark.parametrize("payload", [
    "not json",
    "[]",
    '{"streams": "invalid", "format": {"duration": "2"}}',
    '{"streams": [{"codec_type": "video", "width": true, "height": 180}], "format": {"duration": "2"}}',
    '{"streams": [{"codec_type": "video", "width": 320, "height": 180}], "format": {"duration": "not-a-number"}}',
])
def test_reject_malformed_probe_data(tmp_path, payload):
    source = tmp_path / "malformed.mp4"
    source.write_bytes(b"fixture")
    with patch("app.media_probe.subprocess.run") as run:
        run.return_value.stdout = payload
        with pytest.raises(ValueError):
            inspect_local_video(source)


def test_reject_cover_art_as_video(tmp_path):
    source = tmp_path / "cover.mp4"
    source.write_bytes(b"fixture")
    with patch("app.media_probe.subprocess.run") as run:
        run.return_value.stdout = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 600, "height": 600,
                 "disposition": {"attached_pic": 1}},
                {"codec_type": "audio"},
            ],
            "format": {"duration": "30"},
        })
        with pytest.raises(ValueError, match="no video"):
            inspect_local_video(source)


def test_choose_actual_video_over_cover_art(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"fixture")
    with patch("app.media_probe.subprocess.run") as run:
        run.return_value.stdout = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 600, "height": 600,
                 "disposition": {"attached_pic": 1}},
                {"codec_type": "video", "width": 1920, "height": 1080},
                {"codec_type": "audio"},
            ],
            "format": {"duration": "30"},
        })
        result = inspect_local_video(source)
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert result["has_audio"] is True


@pytest.mark.parametrize("payload", [
    {"streams": [{"codec_type": "video", "width": 320, "height": 180, "disposition": None}], "format": {"duration": "2"}},
    {"streams": [{"codec_type": "video", "width": 320, "height": 180}], "format": None},
    {"streams": [{"codec_type": "video", "width": 320, "height": 180}], "format": {"duration": {}}},
    {"streams": [{"codec_type": "video", "width": 320, "height": 180, "disposition": "bad"}], "format": {"duration": "2"}},
])
def test_probe_handles_unexpected_nested_metadata(tmp_path, payload):
    source = tmp_path / "nested.mp4"
    source.write_bytes(b"fixture")
    with patch("app.media_probe.subprocess.run") as run:
        run.return_value.stdout = json.dumps(payload)
        if (isinstance(payload["format"], dict)
                and isinstance(payload["format"].get("duration"), str)
                and payload["streams"][0].get("disposition") is None):
            assert inspect_local_video(source)["width"] == 320
        else:
            with pytest.raises(ValueError, match="Invalid video metadata"):
                inspect_local_video(source)


def test_choose_usable_secondary_video_stream(tmp_path):
    source = tmp_path / "multi.mp4"
    source.write_bytes(b"fixture")
    with patch("app.media_probe.subprocess.run") as run:
        run.return_value.stdout = json.dumps({
            "streams": [
                {"codec_type": "video", "width": 0, "height": 0},
                {"codec_type": "video", "width": 720, "height": 1280},
            ],
            "format": {"duration": "45"},
        })
        assert inspect_local_video(source)["width"] == 720


@pytest.mark.parametrize("start,end,limit", [
    (-1, 10, 300), (10, 10, 300), (20, 10, 300),
    (0, 46, 300), (0, 40, 30), (float("nan"), 10, 300),
    (0, float("inf"), 300), (0, 10, 0),
    (0, 10, float("nan")), ("bad", 10, 300),
])
def test_reject_invalid_clip_ranges(start, end, limit):
    with pytest.raises(ValueError, match="Invalid clip range"):
        validate_clip_range({"duration_seconds": 45}, start, end,
                            max_duration_seconds=limit)


def test_clip_range_accepts_valid_bounds():
    result = validate_clip_range({"duration_seconds": 45}, "5", 45)
    assert result == {"start_seconds": 5.0, "end_seconds": 45.0,
                      "duration_seconds": 40.0}


def test_clip_range_rejects_missing_duration():
    with pytest.raises(ValueError, match="Invalid clip range"):
        validate_clip_range({}, 0, 10)
