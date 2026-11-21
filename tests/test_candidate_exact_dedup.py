"""Regression tests for duplicate candidate windows and overlap tolerance."""
from app.services.candidates import Candidate, select_candidates


def test_exact_duplicates_rejected_even_with_full_overlap_allowed():
    candidates = [
        Candidate(10, 20, 95, "first"),
        Candidate(10, 20, 90, "duplicate"),
        Candidate(30, 40, 85, "other"),
    ]
    result = select_candidates(candidates, max_overlap_ratio=1.0)
    assert [item.reason for item in result] == ["first", "other"]


def test_millisecond_equivalent_windows_are_duplicates():
    candidates = [
        Candidate(10.0001, 20.0001, 95),
        Candidate(10.0002, 20.0002, 90),
    ]
    assert len(select_candidates(candidates, max_overlap_ratio=1.0)) == 1


def test_distinct_overlapping_windows_allowed_at_full_tolerance():
    candidates = [Candidate(10, 20, 95), Candidate(11, 19, 90)]
    assert len(select_candidates(candidates, max_overlap_ratio=1.0)) == 2


def test_default_tolerance_still_rejects_heavy_overlap():
    candidates = [Candidate(10, 20, 95), Candidate(11, 19, 90)]
    assert len(select_candidates(candidates)) == 1
