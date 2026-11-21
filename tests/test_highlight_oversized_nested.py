"""Oversized nested transcript segments must not hide later valid windows."""
import pytest

from app.intelligence import highlights


@pytest.fixture(autouse=True)
def return_unfiltered_candidates(monkeypatch):
    monkeypatch.setattr(
        highlights, "select_candidates",
        lambda candidates, **kwargs: candidates,
    )


TEXT = (
    "amazing creative moments deserve thoughtful selection and careful editing "
    "before publication with permission from the original creator and a complete "
    "review of every generated clip from this exciting conversation today"
)


def test_oversized_first_segment_does_not_hide_shorter_nested_segment():
    candidates = highlights.score_candidates([
        {"start": 0, "end": 100, "text": "oversized"},
        {"start": 1, "end": 36, "text": TEXT},
    ], maximum_seconds=65)
    assert any(c.start == 1 and c.end == 36 for c in candidates)


def test_oversized_middle_segment_does_not_hide_later_valid_segment():
    candidates = highlights.score_candidates([
        {"start": 0, "end": 10, "text": TEXT},
        {"start": 2, "end": 100, "text": "oversized"},
        {"start": 10, "end": 38, "text": TEXT},
    ], maximum_seconds=65)
    assert any(c.start == 0 and c.end == 38 for c in candidates)


def test_oversized_segment_alone_never_creates_candidate():
    assert highlights.score_candidates([
        {"start": 0, "end": 100, "text": TEXT},
    ], maximum_seconds=65) == []
