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
