from types import SimpleNamespace

import pytest

from app.intelligence.daily_selection import select_daily_clips


def candidate(clip_id, source_id, start, end, score):
    return SimpleNamespace(id=clip_id, source_id=source_id,
                           start_seconds=start, end_seconds=end, score=score)


def test_selects_five_best_across_multiple_sources_without_overlap():
    clips = [
        candidate(1, 10, 0, 30, 98),
        candidate(2, 10, 10, 40, 97),  # overlapping highlight: reject
        candidate(3, 10, 35, 65, 93),
        candidate(4, 10, 70, 100, 90),
        candidate(5, 10, 105, 135, 89),  # source limit: reject
        candidate(6, 20, 0, 30, 92),
        candidate(7, 20, 40, 70, 91),
        candidate(8, 30, 0, 30, 60),  # below quality threshold
    ]
    selected = select_daily_clips(clips)
    assert [clip.clip_id for clip in selected] == [1, 3, 6, 7, 4]
    assert len({clip.clip_id for clip in selected}) == 5


def test_does_not_invent_clips_to_meet_daily_goal():
    selected = select_daily_clips([candidate(1, 10, 0, 30, 80)])
    assert len(selected) == 1


def test_ignores_missing_nonfinite_or_invalid_scores():
    clips = [candidate(1, 1, 0, 30, None),
             candidate(2, 1, 0, 30, float("nan")),
             candidate(3, 1, 20, 10, 95),
             candidate(4, 1, 0, 30, 77)]
    assert [clip.clip_id for clip in select_daily_clips(clips)] == [4]


def test_rejects_invalid_limits():
    with pytest.raises(ValueError):
        select_daily_clips([], target=0)
    with pytest.raises(ValueError):
        select_daily_clips([], max_per_source=0)
