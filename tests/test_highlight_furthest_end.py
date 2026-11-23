"""Regression coverage for nested timed segments and silence boundaries."""
from app.intelligence.highlights import score_candidates


WORDS = "amazing this moment shows why creative highlights deserve careful review before anyone chooses to share a clip with their own audience today"


def test_nested_segment_does_not_break_contiguous_window():
    segments = [
        {"start": 0, "end": 20, "text": WORDS},
        {"start": 1, "end": 2, "text": "wow"},
        {"start": 22, "end": 40, "text": "wait"},
    ]
    candidates = score_candidates(segments, minimum_seconds=35)
    assert candidates
    assert candidates[0].start == 0
    assert candidates[0].end == 40


def test_real_gap_beyond_four_seconds_still_breaks_window():
    segments = [
        {"start": 0, "end": 20, "text": WORDS},
        {"start": 1, "end": 2, "text": "wow"},
        {"start": 25, "end": 43, "text": "wait"},
    ]
    candidates = score_candidates(segments, minimum_seconds=35)
    assert not candidates


def test_single_segment_window_does_not_raise_type_error():
    candidates = score_candidates([{"start": 0, "end": 40, "text": WORDS}])
    assert candidates
    assert candidates[0].end == 40
