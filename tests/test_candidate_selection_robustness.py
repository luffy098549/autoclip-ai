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


def test_submillisecond_window_is_not_selected():
    tiny = Candidate(0.0, 0.0005, 100)
    valid = Candidate(1.0, 2.0, 80)
    assert select_candidates([tiny, valid]) == [valid]


def test_overflowing_duration_is_not_selected():
    huge = Candidate(-1e308, 1e308, 100)
    # Negative start is independently invalid; check a positive start too.
    positive = Candidate(0.0, 1e308, 90)
    valid = Candidate(1.0, 2.0, 80)
    assert select_candidates([huge, positive, valid], threshold=75) == [positive]


def test_finite_but_submillisecond_duration_at_large_offset():
    tiny = Candidate(1000.0, 1000.0001, 99)
    assert select_candidates([tiny]) == []


def test_submillisecond_positive_window_collapses_after_quantization():
    # 1.0001..1.0010 seconds is positive, but both ends truncate to 1000 ms.
    collapsed = Candidate(1.0001, 1.0009, 100)
    valid = Candidate(2.0, 3.0, 80)
    assert select_candidates([collapsed, valid]) == [valid]


def test_overlap_uses_rendered_millisecond_boundaries():
    # Floating-point windows barely overlap, but millisecond truncation
    # makes the first two share the same 1 ms of rendered media.
    first = Candidate(0.0001, 0.0019, 99)
    second = Candidate(0.0011, 0.0029, 98)
    third = Candidate(0.0031, 0.0049, 80)
    assert select_candidates([first, second, third], max_overlap_ratio=0) == [first, third]
