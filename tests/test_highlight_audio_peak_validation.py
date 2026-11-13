"""Regression coverage for malformed optional audio detector output."""
import pytest

from app.intelligence.highlights import score_candidates


SEGMENTS = [{
    "start": 0.0,
    "end": 20.0,
    "text": " ".join(f"palabra{i}" for i in range(30)),
}]


@pytest.mark.parametrize("bad_peak", [
    None, "broken", 1, {}, (), (1,), (1, 0.5, 2),
    (True, 1.0), (1.0, False), ("1", 0.5),
    (1.0, "0.5"), (float("nan"), 1.0),
    (1.0, float("inf")), (float("-inf"), 0.5),
])
def test_malformed_peak_does_not_discard_transcript_candidate(bad_peak):
    baseline = score_candidates(SEGMENTS)
    assert baseline
    result = score_candidates(SEGMENTS, audio_peaks=[bad_peak])
    assert result == baseline


def test_valid_peaks_still_boost_score_and_ignore_outside_window():
    baseline = score_candidates(SEGMENTS)[0]
    result = score_candidates(
        SEGMENTS,
        audio_peaks=[(2, 0.5), (5.0, 1.0), (21.0, 1.0), (1, -2.0)],
    )[0]
    assert result.score == pytest.approx(min(100.0, baseline.score + 6.0))


def test_mixed_valid_and_invalid_peaks_keep_valid_bonus():
    result = score_candidates(
        SEGMENTS, audio_peaks=[None, (2.0, 0.5), ("oops", 1.0)]
    )
    expected = score_candidates(SEGMENTS, audio_peaks=[(2.0, 0.5)])
    assert result == expected


@pytest.mark.parametrize("bad_collection", [
    False, True, 1, 2.5, "not peaks", b"not peaks",
    {"timestamp": 1.0}, object(),
])
def test_malformed_peak_collection_preserves_transcript_score(bad_collection):
    baseline = score_candidates(SEGMENTS)
    assert score_candidates(SEGMENTS, audio_peaks=bad_collection) == baseline


def test_tuple_collection_with_valid_peak_still_scores():
    expected = score_candidates(SEGMENTS, audio_peaks=[(2.0, 0.5)])
    assert score_candidates(SEGMENTS, audio_peaks=((2.0, 0.5),)) == expected
