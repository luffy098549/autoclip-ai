"""Invalid top-level transcript payloads should fail closed without crashing jobs."""
import pytest

from app.intelligence.highlights import score_candidates


@pytest.mark.parametrize("payload", [None, "", "not segments", b"bad", {}, {"segments": []}, 42, True])
def test_invalid_transcript_payload_yields_no_candidates(payload):
    assert score_candidates(payload) == []


def test_tuple_transcript_payload_remains_supported():
    words = (
        "amazing this moment shows why creative highlights deserve careful review "
        "before anyone chooses to share a clip with their own audience today"
    )
    candidates = score_candidates(({"start": 0, "end": 40, "text": words},))
    assert candidates
    assert candidates[0].start == 0
    assert candidates[0].end == 40


def test_invalid_transcript_still_checks_constraints():
    with pytest.raises(ValueError):
        score_candidates(None, max_clips=0)
