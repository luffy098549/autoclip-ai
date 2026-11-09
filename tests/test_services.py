import pytest
from app.services.rights import assess_rights
from app.services.candidates import Candidate, select_candidates
from app.services.subtitles import srt_timestamp, build_srt
from app.services.metadata import sanitize_title
from app.publishers.youtube import upload_short
from app.publishers.base import PublishingDisabled


def test_rights_require_evidence():
    assert not assess_rights("licensed").allowed
    assert assess_rights("owned", "original recording owned by account").allowed
    assert not assess_rights("unverified", "public stream").allowed


def test_highlight_overlap_and_threshold():
    candidates = [
        Candidate(0, 20, 93),
        Candidate(5, 21, 90),
        Candidate(25, 42, 80),
        Candidate(44, 60, 70),
    ]
    assert select_candidates(candidates) == [candidates[0], candidates[2]]


def test_srt_time_format():
    assert srt_timestamp(61.25) == "00:01:01,250"
    assert "00:00:00,000 --> 00:00:02,000" in build_srt([
        {"start": 0, "end": 2, "text": "Hola"}
    ])
    with pytest.raises(ValueError):
        srt_timestamp(-1)


def test_metadata_titles():
    assert sanitize_title("   Hola   mundo   ") == "Hola mundo"
    with pytest.raises(ValueError):
        sanitize_title(" ")


def test_youtube_upload_disabled():
    with pytest.raises(PublishingDisabled):
        upload_short("clip.mp4")
