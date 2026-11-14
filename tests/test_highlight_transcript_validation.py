"""Regression tests for malformed transcript input at the scoring boundary."""
import pytest

from app.intelligence.highlights import score_candidates


VALID = {
    "start": 0.0,
    "end": 20.0,
    "text": " ".join(f"word{i}" for i in range(30)),
}


@pytest.mark.parametrize("bad_segment", [
    None, 42, "bad", [], {}, {"start": True, "end": 20, "text": "words"},
    {"start": "0", "end": 20, "text": "words"},
    {"start": 0, "end": "20", "text": "words"},
    {"start": 0, "end": 20, "text": {"invalid": "text"}},
    {"start": float("nan"), "end": 20, "text": "words"},
    {"start": 0, "end": float("inf"), "text": "words"},
])
def test_invalid_segment_is_ignored_without_losing_valid_candidates(bad_segment):
    baseline = score_candidates([VALID])
    assert baseline
    assert score_candidates([bad_segment, VALID]) == baseline


@pytest.mark.parametrize("bad_collection", [None, 123, "not segments", {}, True])
def test_invalid_transcript_collection_returns_no_candidates(bad_collection):
    assert score_candidates(bad_collection) == []


def test_tuple_of_valid_transcript_segments_is_supported():
    assert score_candidates((VALID,)) == score_candidates([VALID])


def test_missing_text_is_treated_as_empty_and_does_not_crash():
    assert score_candidates([{"start": 0, "end": 20}]) == []
