"""End-to-end FFmpeg smoke test using only locally generated synthetic media."""
import shutil
import subprocess

import pytest

from app.pipeline import create_local_clip
from app.quality import inspect_video


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and ffprobe are required for the integration test",
)
def test_synthetic_authorized_video_renders_vertical_mp4_with_audio(tmp_path):
    source = tmp_path / "synthetic-owned.mp4"
    output = tmp_path / "clips" / "vertical.mp4"
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=15",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
            "-t", "3", "-c:v", "mpeg4", "-q:v", "5", "-c:a", "aac",
            "-shortest", str(source),
        ],
        check=True, timeout=60,
    )
    result = create_local_clip(source, output, start=0.5, end=2.5, authorized=True)
    assert output.is_file()
    assert result["path"] == str(output)
    info = inspect_video(output)
    assert (info["width"], info["height"]) == (1080, 1920)
    assert info["has_audio"]
    assert 1.5 <= info["duration"] <= 2.6
    assert result["export"]["width"] == 1080
    assert result["export"]["height"] == 1920
