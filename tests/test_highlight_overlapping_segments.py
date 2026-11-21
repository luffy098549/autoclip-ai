"""Overlapping Whisper segments must never truncate a highlight window."""
from app.intelligence.highlights import score_candidates


def test_nested_segments_do_not_shorten_candidate_end():
    words = " ".join(["amazing"] * 25)
    segments = [
        {"start": 0, "end": 40, "text": words},
        {"start": 5, "end": 10, "text": "wow"},
        {"start": 15, "end": 20, "text": "wait"},
    ]
    candidates = score_candidates(segments)
    assert candidates
    assert all(not (c.start == 0 and c.end < 40) for c in candidates)
    assert candidates[0].start == 0
    assert candidates[0].end == 40


def test_partially_overlapping_segments_cover_full_window():
    words = " ".join(["amazing"] * 25)
    segments = [
        {"start": 0, "end": 25, "text": words},
        {"start": 15, "end": 35, "text": "wow"},
    ]
    candidates = score_candidates(segments)
    assert candidates
    assert candidates[0].start == 0
    assert candidates[0].end == 35
