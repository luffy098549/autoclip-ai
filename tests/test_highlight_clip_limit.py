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
