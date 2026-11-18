"""Real FFmpeg smoke test using only generated, license-free synthetic media."""
import json
import shutil
import subprocess

import pytest

from app.video import render_vertical_clip


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools unavailable")
def test_synthetic_landscape_source_exports_vertical_video_without_audio(tmp_path):
    source = tmp_path / "synthetic.mp4"
    target = tmp_path / "vertical.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=12:d=1",
        "-an", "-c:v", "mpeg4", str(source),
    ], check=True, timeout=30)
    original = source.read_bytes()

    assert render_vertical_clip(source, target, 0, 1) == str(target)
    assert source.read_bytes() == original
    assert target.stat().st_size > 0
    assert not list(tmp_path.glob(".autoclip-*.mp4"))

    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,codec_type,width,height,pix_fmt", "-of", "json", str(target),
    ], check=True, capture_output=True, text=True, timeout=30)
    streams = json.loads(probe.stdout)["streams"]
    videos = [stream for stream in streams if stream["codec_type"] == "video"]
    assert len(videos) == 1
    assert videos[0]["codec_name"] == "h264"
    assert (videos[0]["width"], videos[0]["height"]) == (1080, 1920)
    assert videos[0]["pix_fmt"] == "yuv420p"
    assert not any(stream["codec_type"] == "audio" for stream in streams)
