"""Reject malformed model text before it reaches PostgreSQL or subtitles."""
import pytest

from app.services.analyzer import _validate_transcription


@pytest.mark.parametrize("language", [
    "es\x00", "\nes", "en\tUS", "fr\r", "de\x1f", "es\x7f",
])
def test_language_control_characters_rejected(language):
    with pytest.raises(ValueError, match="language"):
        _validate_transcription({"language": language, "segments": []})


@pytest.mark.parametrize("caption", ["hello\x00world", "\x00", "  \x00  "])
def test_caption_nul_rejected(caption):
    with pytest.raises(ValueError, match="text"):
        _validate_transcription({"language": "es", "segments": [
            {"start": 0, "end": 1, "text": caption},
        ]})


def test_valid_unicode_caption_and_language_preserved():
    assert _validate_transcription({"language": " es ", "segments": [
        {"start": 0, "end": 1.25, "text": "  ¡Hola, mundo! 🎬  "},
    ]}) == ("es", [(0.0, 1.25, "¡Hola, mundo! 🎬")])


def test_newlines_in_captions_remain_supported():
    assert _validate_transcription({"language": "en", "segments": [
        {"start": 0, "end": 2, "text": "First line\nSecond line"},
    ]})[1][0][2] == "First line\nSecond line"
