"""Ensure untrusted audio sources cannot cause FFmpeg to fetch remote URLs."""
import os
import pytest
from app.intelligence import audio_peaks


@pytest.mark.parametrize("invalid", [
    None, 1, True, "", "  ", "https://example.invalid/video",
    "http://example.invalid/audio", "pipe:0", "concat:secret",
    "missing-file.wav", "bad\\x00name",
])
def test_reject_invalid_or_nonlocal_audio_without_spawning(monkeypatch, tmp_path, invalid):
    monkeypatch.chdir(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("FFmpeg must not start")
    monkeypatch.setattr(audio_peaks.subprocess, "Popen", forbidden)
    with pytest.raises(ValueError, match="Invalid audio path"):
        audio_peaks.detect_audio_peaks(invalid)


def test_reject_directory_without_spawning(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_peaks.subprocess, "Popen", lambda *a, **k: pytest.fail("FFmpeg started"))
    with pytest.raises(ValueError, match="Invalid audio path"):
        audio_peaks.detect_audio_peaks(tmp_path)


def test_existing_local_file_reaches_ffmpeg(monkeypatch, tmp_path):
    audio = tmp_path / "authorized.wav"
    audio.write_bytes(b"RIFF")
    calls = []
    def fake_popen(command, **kwargs):
        calls.append(command)
        raise RuntimeError("fake FFmpeg invoked")
    monkeypatch.setattr(audio_peaks.subprocess, "Popen", fake_popen)
    with pytest.raises(RuntimeError, match="fake FFmpeg invoked"):
        audio_peaks.detect_audio_peaks(os.fspath(audio))
    assert len(calls) == 1
    assert calls[0][calls[0].index("-protocol_whitelist") + 1] == "file,pipe"
    assert calls[0][calls[0].index("-i") + 1] == os.fspath(audio)


def test_protocol_like_local_filename_still_uses_restricted_protocols(monkeypatch, tmp_path):
    """A local filename can resemble an FFmpeg protocol; never enable network protocols."""
    audio = tmp_path / "concat:local.wav"
    audio.write_bytes(b"RIFF")
    commands = []
    def fake_popen(command, **kwargs):
        commands.append(command)
        raise RuntimeError("mock FFmpeg")
    monkeypatch.setattr(audio_peaks.subprocess, "Popen", fake_popen)
    with pytest.raises(RuntimeError, match="mock FFmpeg"):
        audio_peaks.detect_audio_peaks(audio)
    assert commands
    assert commands[0][commands[0].index("-protocol_whitelist") + 1] == "file,pipe"


def test_nul_path_rejected_before_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_peaks.subprocess, "Popen", lambda *a, **k: pytest.fail("FFmpeg started"))
    with pytest.raises(ValueError, match="Invalid audio path"):
        audio_peaks.detect_audio_peaks(str(tmp_path / "audio") + chr(0) + ".wav")
