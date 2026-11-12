import math

import pytest

from app.services.rights import assess_rights
from app.services.candidates import Candidate, select_candidates
from app.services.subtitles import build_srt, srt_timestamp


def test_rights_require_evidence_for_owned_or_licensed():
    assert assess_rights("owned", "I recorded this video").allowed
    assert assess_rights("licensed", "License agreement #123").allowed
    assert not assess_rights("owned", "").allowed
    assert not assess_rights("unverified", "I think it is okay").allowed
    assert not assess_rights("denied", "permission").allowed


def test_candidate_selection_ranks_and_limits_results():
    candidates = [
        Candidate(0, 30, 80),
        Candidate(31, 61, 95),
        Candidate(62, 92, 70),
        Candidate(93, 123, 90),
    ]
    selected = select_candidates(candidates, threshold=75, max_count=2)
    assert [item.score for item in selected] == [95, 90]


def test_candidate_selection_rejects_invalid_and_overlapping_ranges():
    candidates = [
        Candidate(0, 30, 90),
        Candidate(2, 28, 99),  # near-duplicate of the first range
        Candidate(-1, 10, 100),
        Candidate(40, 20, 100),
        Candidate(50, 80, math.nan),
        Candidate(90, 120, 60),
    ]
    selected = select_candidates(candidates, threshold=65)
    assert len(selected) == 1
    assert selected[0].start == 2


def test_srt_timestamp_and_subtitle_export_format():
    assert srt_timestamp(65.25) == "00:01:05,250"
    output = build_srt([
        {"start": 0, "end": 1.25, "text": "  Hello world  "},
        {"start": 1.25, "end": 2, "text": "Second line"},
    ])
    assert "1\n00:00:00,000 --> 00:00:01,250\nHello world" in output
    assert "2\n00:00:01,250 --> 00:00:02,000\nSecond line" in output


def test_srt_rejects_non_positive_segment_duration():
    with pytest.raises(ValueError):
        build_srt([{"start": 2, "end": 2, "text": "invalid"}])
