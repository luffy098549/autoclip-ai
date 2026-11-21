"""Malformed timing and nonverbal captions must not bridge spoken segments."""
import pytest
from app.intelligence import highlights


TEXT = (
    "amazing original licensed footage contains carefully chosen dialogue "
    "that helps reviewers identify interesting moments with clear context "
    "and confirm each resulting clip before any public distribution"
)


@pytest.fixture(autouse=True)
def retain_candidates(monkeypatch):
    monkeypatch.setattr(highlights, "select_candidates", lambda items, **kwargs: items)


@pytest.mark.parametrize("field", ["start", "end"])
@pytest.mark.parametrize("value", [True, False])
def test_boolean_timestamps_are_ignored(field, value):
    invalid = {"start": 31, "end": 59, "text": TEXT}
    invalid[field] = value
    result = highlights.score_candidates([
        {"start": 0, "end": 30, "text": TEXT},
        invalid,
    ])
    assert [(item.start, item.end) for item in result] == [(0, 30)]


@pytest.mark.parametrize("caption", ["!!! ???", "🎬🔥", "\u200b\u200d", "  ...  "])
def test_nonverbal_captions_cannot_bridge_a_gap(caption):
    result = highlights.score_candidates([
        {"start": 0, "end": 30, "text": TEXT},
        {"start": 31, "end": 59, "text": caption},
        {"start": 60, "end": 90, "text": TEXT},
    ])
    assert [(item.start, item.end) for item in result] == [(0, 30), (60, 90)]


def test_spoken_caption_with_punctuation_is_kept():
    result = highlights.score_candidates([
        {"start": 0, "end": 30, "text": TEXT + "!!!"},
    ])
    assert len(result) == 1
    assert result[0].end == 30
