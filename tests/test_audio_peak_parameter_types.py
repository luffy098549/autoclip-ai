"""Validate untrusted audio analysis settings before launching FFmpeg."""

import math

import pytest

from app.intelligence import audio_peaks


@pytest.mark.parametrize("invalid", [None, True, False, "1", b"1", [], {}, float("nan"), float("inf"), -float("inf"), 0, -1, 0.09, 10.01])
def test_invalid_interval_rejected_without_starting_ffmpeg(monkeypatch, invalid):
    def forbidden(*args, **kwargs):
        raise AssertionError("FFmpeg must not start for invalid settings")

    monkeypatch.setattr(audio_peaks.subprocess, "Popen", forbidden)
    with pytest.raises(ValueError, match="Invalid interval_seconds"):
        audio_peaks.detect_audio_peaks("authorized.wav", interval_seconds=invalid)


@pytest.mark.parametrize("invalid", [None, True, False, "120", b"120", [], {}, float("nan"), float("inf"), -float("inf"), 0, -1, 0.99, 7200.01])
def test_invalid_maximum_duration_rejected_without_starting_ffmpeg(monkeypatch, invalid):
    def forbidden(*args, **kwargs):
        raise AssertionError("FFmpeg must not start for invalid settings")

    monkeypatch.setattr(audio_peaks.subprocess, "Popen", forbidden)
    with pytest.raises(ValueError, match="Invalid maximum_seconds"):
        audio_peaks.detect_audio_peaks("authorized.wav", maximum_seconds=invalid)
