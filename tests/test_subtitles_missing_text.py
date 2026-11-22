"""Regression coverage for missing transcript text in SRT output."""

from app.services.subtitles import build_srt


def test_missing_transcript_text_is_not_rendered_as_none():
    cues = [
        {"start": 0, "end": 1, "text": None},
        {"start": 1, "end": 2},
        {"start": 2, "end": 3, "text": "Actual dialogue"},
    ]
    result = build_srt(cues)
    assert result.count(" --> ") == 1
    assert "Actual dialogue" in result
    assert "None" not in result
    assert result.startswith("1\n")


def test_structured_provider_metadata_is_not_rendered_as_dialogue():
    cues = [
        {"start": 0, "end": 1, "text": {"word": "not spoken"}},
        {"start": 1, "end": 2, "text": ["not", "spoken"]},
        {"start": 2, "end": 3, "text": 12345},
        {"start": 3, "end": 4, "text": "Real words"},
    ]
    result = build_srt(cues)
    assert result.count(" --> ") == 1
    assert "Real words" in result
    assert "not spoken" not in result
    assert "12345" not in result
    assert result.startswith("1\\n")
