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
    # Both huge windows exceed the supported one-day clip duration.\n    assert select_candidates([huge, positive, valid], threshold=75) == [valid]


def test_finite_but_submillisecond_duration_at_large_offset():
    tiny = Candidate(1000.0, 1000.0001, 99)
    assert select_candidates([tiny]) == []


def test_adjacent_rendered_windows_are_not_deduplicated():
    first = Candidate(1.0001, 1.0021, 99)
    second = Candidate(1.0021, 1.0041, 98)
    assert select_candidates([first, second], max_overlap_ratio=0) == [first, second]


def test_overlap_uses_rendered_millisecond_boundaries():
    # Float overlap is 40%, but rendered millisecond overlap is 50%.
    first = Candidate(0.0001, 0.0021, 99)
    second = Candidate(0.0013, 0.0033, 98)
    third = Candidate(0.0051, 0.0073, 80)
    assert select_candidates([first, second, third], max_overlap_ratio=0.45) == [first, third]


@pytest.mark.parametrize("overlap", [-0.1, 1.1, True, None, "0.25", math.inf, math.nan, 10 ** 1000])
def test_invalid_overlap_rejected(overlap):
    with pytest.raises(ValueError):
        select_candidates([Candidate(0, 20, 90)], max_overlap_ratio=overlap)


def test_extremely_large_positive_start_is_skipped_without_overflow():
    unrenderable = Candidate(1e308, 1.1e308, 99)
    valid = Candidate(0, 10, 80)
    assert select_candidates([unrenderable, valid]) == [valid]


def test_duration_limit_accepts_one_day_and_rejects_longer():
    allowed = Candidate(0, 86400, 90)
    too_long = Candidate(0, 86400.001, 99)
    assert select_candidates([too_long, allowed]) == [allowed]
