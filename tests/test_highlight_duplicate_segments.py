"""Repeated provider segments must not inflate highlight scores or duration."""
from app.intelligence import highlights


TEXT = (
    "amazing creators share thoughtful stories and exciting moments with audiences "
    "while editors carefully review each recording before selecting a final clip "
    "for a permitted publication across their own channels"
)


def test_identical_segments_are_not_counted_twice(monkeypatch):
    monkeypatch.setattr(
        highlights, "select_candidates", lambda candidates, **kwargs: candidates
    )
    segment = {"start": 0, "end": 20, "text": TEXT}
    single = highlights.score_candidates([segment])
    repeated = highlights.score_candidates([segment, segment, segment])
    assert repeated == single
    assert len(repeated) == 1


def test_same_timestamps_with_different_text_are_preserved(monkeypatch):
    monkeypatch.setattr(
        highlights, "select_candidates", lambda candidates, **kwargs: candidates
    )
    first = {"start": 0, "end": 20, "text": TEXT}
    second = {"start": 0, "end": 20, "text": "wait " + TEXT}
    results = highlights.score_candidates([first, second])
    assert results
    assert any(candidate.start == 0 and candidate.end == 20 for candidate in results)


def test_duplicates_do_not_change_final_selection():
    segment = {"start": 0, "end": 20, "text": TEXT}
    assert highlights.score_candidates([segment] * 4) == highlights.score_candidates([segment])
