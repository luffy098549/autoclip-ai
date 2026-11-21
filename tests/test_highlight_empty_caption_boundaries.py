"""Empty captions must not distort highlight boundaries or bridge transcript gaps."""
import pytest
from app.intelligence import highlights


@pytest.fixture(autouse=True)
def retain_candidates(monkeypatch):
    monkeypatch.setattr(highlights, "select_candidates", lambda items, **kwargs: items)


TEXT = (
    "amazing original licensed footage contains carefully chosen dialogue "
    "that helps reviewers identify interesting moments with clear context "
    "and confirm each resulting clip before any public distribution"
)


def test_empty_caption_does_not_bridge_long_gap():
    segments = [
        {"start": 0, "end": 30, "text": TEXT},
        {"start": 31, "end": 59, "text": "   "},
        {"start": 60, "end": 90, "text": TEXT},
    ]
    result = highlights.score_candidates(segments)
    assert len(result) == 2
    assert [(x.start, x.end) for x in result] == [(0, 30), (60, 90)]


@pytest.mark.parametrize("bad_text", [None, [], {}, "", "\t\n"])
def test_invalid_or_blank_caption_does_not_extend_valid_window(bad_text):
    segments = [
        {"start": 0, "end": 30, "text": TEXT},
        {"start": 30, "end": 55, "text": bad_text},
    ]
    result = highlights.score_candidates(segments)
    assert len(result) == 1
    assert result[0].start == 0
    assert result[0].end == 30


def test_empty_transcript_returns_no_candidates():
    assert highlights.score_candidates([
        {"start": 0, "end": 40, "text": " "},
        {"start": 40, "end": 80, "text": None},
    ]) == []
