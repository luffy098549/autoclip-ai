"""Real faster-whisper smoke test with locally synthesized speech.

This test downloads the public tiny.en model on first run. No user media or
credentials are needed. Unlike mocked unit tests, inference actually executes.
"""
import shutil
import subprocess

import pytest

from app.services.transcription import transcribe_file


@pytest.mark.skipif(
    not shutil.which("espeak-ng") or not shutil.which("ffmpeg"),
    reason="espeak-ng and FFmpeg are required to synthesize local speech",
)
def test_real_whisper_transcribes_synthetic_spoken_audio(tmp_path):
    wav = tmp_path / "owned-synthetic-speech.wav"
    subprocess.run([
        "espeak-ng", "-v", "en-us", "-s", "125",
        "-w", str(wav),
        "Hello there. This is an original test recording. "
        "We are checking that speech recognition works correctly.",
    ], check=True, timeout=30)
    result = transcribe_file(str(wav), model_size="tiny.en", device="cpu")
    assert result["segments"], "Real Whisper did not detect synthetic spoken words"
    assert any(segment["text"].strip() for segment in result["segments"])
    assert all(segment["end"] > segment["start"] >= 0 for segment in result["segments"])
    assert result["language"] in {"en", "english"}
