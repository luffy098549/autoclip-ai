"""Reject malformed clip limits before analyzing any transcript."""

import pytest

from app.intelligence.highlights import score_candidates


@pytest.mark.parametrize("limit", [True, False, 0, -1, 6, 1.5, 3.0, "3", None, [], {}])
def test_highlight_rejects_invalid_max_clips(limit):
    with pytest.raises(ValueError, match="Invalid duration constraints"):
        score_candidates([], max_clips=limit)


@pytest.mark.parametrize("limit", [1, 2, 3, 4, 5])
def test_highlight_accepts_integer_clip_limits(limit):
    assert score_candidates([], max_clips=limit) == []


@pytest.mark.parametrize("field", ["minimum_seconds", "maximum_seconds"])
@pytest.mark.parametrize("value", [True, False, None, "18", [], {}, float("nan"), float("inf"), float("-inf")])
def test_highlight_rejects_malformed_duration_types(field, value):
    with pytest.raises(ValueError, match="Invalid duration constraints"):
        score_candidates([], **{field: value})


def test_highlight_accepts_integer_and_float_durations():
    assert score_candidates([], minimum_seconds=18, maximum_seconds=65.0) == []
