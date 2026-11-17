"""Regression tests for robust, deterministic top-five candidate selection."""
import math
import pytest
from app.services.candidates import Candidate, select_candidates


@pytest.mark.parametrize("count", [0, 6, True, 1.5, "5"])
def test_invalid_max_count_rejected(count):
    with pytest.raises(ValueError):
        select_candidates([Candidate(0, 20, 90)], max_count=count)


@pytest.mark.parametrize("threshold", [-1, 101, True, "75", 10 ** 1000, math.nan])
def test_invalid_threshold_rejected(threshold):
    with pytest.raises(ValueError):
        select_candidates([], threshold=threshold)


def test_bad_candidates_are_ignored_before_sorting():
    good = Candidate(0, 20, 90)
    malformed = [Candidate(1, 20, math.nan), Candidate(True, 20, 95),
                 Candidate(1, 20, "high"), Candidate(1, 20, 10 ** 1000),
                 None, {"score": 100}]
    assert select_candidates(malformed + [good]) == [good]


def test_top_five_are_deterministic_and_nonoverlapping():
    choices = [Candidate(i * 30, i * 30 + 20, 90) for i in range(8)]
    assert select_candidates(list(reversed(choices))) == choices[:5]


def test_overlap_rejects_near_duplicate_windows():
    high = Candidate(0, 30, 95)
    duplicate = Candidate(5, 35, 94)
    independent = Candidate(40, 65, 80)
    assert select_candidates([duplicate, independent, high]) == [high, independent]
