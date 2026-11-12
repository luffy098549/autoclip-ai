import math

from app.services.candidates import Candidate, select_candidates


def test_candidate_selection_rejects_non_finite_threshold():
    candidate = Candidate(0, 30, 99)
    for threshold in (math.nan, math.inf, -math.inf):
        try:
            select_candidates([candidate], threshold=threshold)
        except ValueError:
            pass
        else:
            raise AssertionError("Non-finite threshold must be rejected")


def test_candidate_selection_rejects_invalid_overlap_ratio():
    candidate = Candidate(0, 30, 99)
    for ratio in (math.nan, math.inf, -math.inf):
        try:
            select_candidates([candidate], max_overlap_ratio=ratio)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid overlap ratio must be rejected")


def test_nonfinite_candidate_cannot_displace_valid_candidate():
    candidates = [
        Candidate(0, 30, math.nan),
        Candidate(40, 70, 95),
        Candidate(80, 110, math.inf),
        Candidate(120, 150, 90),
    ]
    selected = select_candidates(candidates, max_count=2)
    assert [c.score for c in selected] == [95, 90]


def test_candidate_selection_rejects_non_integer_limits():
    import pytest
    candidate = Candidate(0, 30, 90)
    for count in (True, 1.5, 0, -1):
        with pytest.raises(ValueError):
            select_candidates([candidate], max_count=count)
