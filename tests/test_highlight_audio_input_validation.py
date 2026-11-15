"""Regression tests for malformed highlight settings and optional audio peaks."""
import pytest
from app.intelligence import highlights


@pytest.fixture(autouse=True)
def raw_candidates(monkeypatch):
    monkeypatch.setattr(highlights, "select_candidates", lambda candidates, **kwargs: candidates)


def segments():
    return [{"start": 0, "end": 30, "text": " ".join(["ordinary"] * 25)}]


@pytest.mark.parametrize("kwargs", [
    {"minimum_seconds": None}, {"minimum_seconds": True},
    {"minimum_seconds": "18"}, {"minimum_seconds": 10 ** 400},
    {"maximum_seconds": False}, {"maximum_seconds": float("nan")},
    {"maximum_seconds": 10 ** 400}, {"max_clips": True},
    {"max_clips": 1.5}, {"max_clips": "5"}, {"max_clips": 6},
])
def test_invalid_constraints_fail_before_scoring(kwargs):
    with pytest.raises(ValueError, match="Invalid duration constraints"):
        highlights.score_candidates(segments(), **kwargs)


@pytest.mark.parametrize("peaks", [
    None, "bad", {"timestamp": 2}, [(1,)], [(1, 2, 3)],
    [(None, 1)], [("2", 1)], [(2, "1")], [(True, 1)],
    [(2, float("nan"))], [(10 ** 400, 1)], [None],
])
def test_malformed_audio_peaks_do_not_crash(peaks):
    baseline = highlights.score_candidates(segments())
    assert highlights.score_candidates(segments(), audio_peaks=peaks) == baseline


def test_valid_audio_peaks_still_increase_score():
    baseline = highlights.score_candidates(segments())[0].score
    boosted = highlights.score_candidates(segments(), audio_peaks=[(2.0, 1.0)])[0].score
    assert boosted > baseline


def test_mixed_audio_peaks_preserve_valid_entries():
    mixed = highlights.score_candidates(segments(), audio_peaks=[None, (2.0, 1.0), (3, "bad")])
    valid = highlights.score_candidates(segments(), audio_peaks=[(2.0, 1.0)])
    assert mixed == valid
