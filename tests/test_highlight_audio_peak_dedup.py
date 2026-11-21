"""Audio frames must not boost highlight scores when duplicated by providers."""
import pytest

from app.intelligence import highlights


@pytest.fixture(autouse=True)
def keep_raw_candidates(monkeypatch):
    monkeypatch.setattr(
        highlights, "select_candidates",
        lambda candidates, **kwargs: candidates,
    )


def transcript():
    return [{
        "start": 0, "end": 40,
        "text": (
            "amazing creative moments deserve thoughtful selection and careful "
            "editing before publication with permission from the original "
            "creator and a complete review of every generated clip today"
        ),
    }]


def score(peaks):
    candidates = highlights.score_candidates(transcript(), audio_peaks=peaks)
    assert len(candidates) == 1
    return candidates[0].score


def test_repeated_audio_timestamp_does_not_inflate_score():
    assert score([(5, 0.8)] * 8) == score([(5, 0.8)])


def test_duplicate_audio_timestamp_uses_strongest_peak():
    assert score([(5, 0.1), (5, 0.8), (5, 0.4)]) == score([(5, 0.8)])
    assert score([(5, 0.8), (5, 0.1)]) == score([(5, 0.8)])


def test_distinct_audio_timestamps_remain_additive():
    assert score([(5, 0.8), (6, 0.8)]) > score([(5, 0.8)])


def test_negative_audio_timestamps_are_ignored():
    assert score([(-1, 1.0), (5, 0.8)]) == score([(5, 0.8)])
