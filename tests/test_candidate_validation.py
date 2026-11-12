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
