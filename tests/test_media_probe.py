"""Tests for local-only metadata inspection using synthetic inputs."""
import json
import shutil
import subprocess
from unittest.mock import patch

import pytest
from app.media_probe import inspect_local_video


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
