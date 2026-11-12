"""Real FFmpeg regression for local audio energy detection."""
import shutil
import subprocess

import pytest
from app.intelligence.audio_peaks import detect_audio_peaks


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg required")
def test_audio_peaks_detect_loud_section(tmp_path):
    output = tmp_path / "generated-owned-audio.wav"
    subprocess.run([
        "ffmpeg", "-nostdin", "-v", "error", "-y",
        "-f", "lavfi", "-i",
        "aevalsrc=if(lt(t\\,2)\\,0.01*sin(2*PI*440*t)\\,0.8*sin(2*PI*440*t)):s=8000:d=4",
        str(output),
    ], check=True, timeout=30)
    peaks = detect_audio_peaks(str(output), interval_seconds=1)
    assert peaks
    assert any(2 <= time < 4 for time, strength in peaks if strength > 0.5)
    assert all(0 <= strength <= 1 for _, strength in peaks)
