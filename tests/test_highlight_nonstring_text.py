"""Malformed provider text must not become fabricated transcript words."""
import pytest
from app.intelligence import highlights


class ExplodingText:
    def __str__(self):
        raise RuntimeError("provider object must never be stringified")


@pytest.fixture(autouse=True)
def keep_candidates(monkeypatch):
    monkeypatch.setattr(highlights, "select_candidates", lambda items, **kwargs: items)


@pytest.mark.parametrize("invalid", [
    {"unexpected": "amazing " * 30},
    ["amazing"] * 30,
    123,
    True,
    ExplodingText(),
])
def test_non_string_text_is_ignored_without_crashing(invalid):
    segments = [{"start": 0, "end": 40, "text": invalid}]
    assert highlights.score_candidates(segments) == []


def test_bad_text_does_not_hide_later_valid_transcript():
    good = (
        "amazing creative editing can help audiences discover moments "
        "when content owners have explicitly approved the use of their "
        "original video and reviewed the resulting highlight before sharing"
    )
    segments = [
        {"start": 0, "end": 40, "text": ExplodingText()},
        {"start": 50, "end": 90, "text": good},
    ]
    result = highlights.score_candidates(segments)
    assert len(result) == 1
    assert result[0].start == 50
    assert result[0].end == 90


def test_empty_text_and_valid_text_behave_consistently():
    valid = "amazing " + "carefully selected original licensed content " * 6
    for text in (None, "", [], {}):
        result = highlights.score_candidates([
            {"start": 0, "end": 40, "text": text},
            {"start": 50, "end": 90, "text": valid},
        ])
        assert len(result) == 1
        assert result[0].start == 50
