"""Malformed provider segment entries must not abort highlight extraction."""
from app.intelligence.highlights import score_candidates


WORDS = (
    "amazing this moment shows why creative highlights deserve careful review "
    "before anyone chooses to share a clip with their own audience today"
)


def test_non_mapping_entries_are_ignored():
    segments = [
        None,
        "unexpected transcript entry",
        ["not", "a", "segment"],
        {"start": 0, "end": 40, "text": WORDS},
    ]
    candidates = score_candidates(segments)
    assert candidates
    assert candidates[0].start == 0
    assert candidates[0].end == 40


def test_only_malformed_entries_produce_no_candidates():
    assert score_candidates([None, 42, "bad", [], {}]) == []
