"""Regression tests for local Whisper transcription normalization."""
import sys
import types
from types import SimpleNamespace

import pytest

from app.services.transcription import transcribe_file


def test_transcribe_skips_malformed_and_zero_length_cues(tmp_path, monkeypatch):
    source = tmp_path / "authorized.wav"
    source.write_bytes(b"fixture")

    cues = [
        SimpleNamespace(start=0.0, end=1.234, text=" hello "),
        SimpleNamespace(start=2.0, end=2.0001, text="too short"),
        SimpleNamespace(start=float("nan"), end=3.0, text="invalid"),
        SimpleNamespace(start=-1.0, end=1.0, text="negative"),
        SimpleNamespace(start="bad", end=2.0, text="invalid"),
        SimpleNamespace(start=4.0, end=5.0, text="safe\\x00 text"),
    ]

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, *args, **kwargs):
            return iter(cues), SimpleNamespace(language="es")

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    result = transcribe_file(str(source))
    assert result == {
        "language": "es",
        "segments": [
            {"start": 0.0, "end": 1.234, "text": "hello"},
            {"start": 4.0, "end": 5.0, "text": "safe text"},
        ],
    }


def test_transcribe_rejects_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        transcribe_file(str(tmp_path / "missing.wav"))
