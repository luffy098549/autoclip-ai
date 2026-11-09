"""Optional FFmpeg smoke test using synthetic media; no third-party content."""
import shutil
import subprocess
import pytest
from app.pipeline import create_local_clip


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg and ffprobe are required")
def test_local_render_from_synthetic_video(tmp_path):
    source = tmp_path / "generated.mp4"
    output = tmp_path / "clip.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:r=8:d=2",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-shortest", "-c:v", "mpeg4", "-c:a", "aac",
        str(source)
    ], check=True, timeout=40)
    info = create_local_clip(source, output, start=0, end=1.5, authorized=True)
    assert info["export"]["width"] == 1080
    assert info["export"]["height"] == 1920
    assert info["export"]["has_audio"]
    assert output.exists()
