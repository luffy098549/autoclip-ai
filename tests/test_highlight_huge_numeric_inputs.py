"""Guard numeric boundaries against Python integer-to-float overflow."""
import pytest

from app.intelligence.highlights import score_candidates


SEGMENT = {"start": 0, "end": 20, "text": " ".join(f"word{i}" for i in range(30))}
HUGE = 10 ** 1000


@pytest.mark.parametrize("field", ["minimum_seconds", "maximum_seconds"])
def test_huge_duration_setting_is_rejected(field):
    with pytest.raises(ValueError, match="Invalid duration constraints"):
        score_candidates([SEGMENT], **{field: HUGE})


@pytest.mark.parametrize("field", ["start", "end"])
def test_huge_transcript_timestamp_is_ignored(field):
    invalid = {**SEGMENT, field: HUGE}
    assert score_candidates([invalid, SEGMENT]) == score_candidates([SEGMENT])


@pytest.mark.parametrize("peak", [(HUGE, 1.0), (1.0, HUGE), (-HUGE, 0.5)])
def test_huge_audio_peak_is_ignored(peak):
    assert score_candidates([SEGMENT], audio_peaks=[peak]) == score_candidates([SEGMENT])


def test_normal_numeric_peak_still_increases_score():
    baseline = score_candidates([SEGMENT])[0].score
    boosted = score_candidates([SEGMENT], audio_peaks=[(1, 0.5)])[0].score
    assert boosted == pytest.approx(min(100.0, baseline + 2.0))

def test_mixed_peak_inputs_preserve_valid_peak_scoring():
    valid = [(1.0, 0.5), (3, 1.0), (30, 1.0)]
    mixed = [None, "invalid", (1,), (True, 1.0), (2, float("nan")), *valid]
    assert score_candidates([SEGMENT], audio_peaks=mixed) == score_candidates(
        [SEGMENT], audio_peaks=valid
    )


def test_many_invalid_peaks_do_not_change_candidate_score():
    baseline = score_candidates([SEGMENT])
    malformed = [(float("inf"), 1.0), (1.0, float("nan")), None] * 100
    assert score_candidates([SEGMENT], audio_peaks=malformed) == baseline


def test_duplicate_peak_timestamps_count_only_once():
    once = score_candidates([SEGMENT], audio_peaks=[(1, 0.5)])
    repeated = score_candidates([SEGMENT], audio_peaks=[(1, 0.5)] * 20)
    assert repeated == once


def test_same_timestamp_uses_strongest_peak_independent_of_order():
    strongest = score_candidates([SEGMENT], audio_peaks=[(1, 0.8)])
    assert score_candidates([SEGMENT], audio_peaks=[(1, 0.2), (1, 0.8)]) == strongest
    assert score_candidates([SEGMENT], audio_peaks=[(1, 0.8), (1, 0.2)]) == strongest


def test_negative_and_zero_strength_peaks_do_not_affect_score():
    baseline = score_candidates([SEGMENT])
    assert score_candidates([SEGMENT], audio_peaks=[(-1, 1), (1, -2), (2, 0)]) == baseline


def test_distinct_timestamps_still_contribute_independently():
    one = score_candidates([SEGMENT], audio_peaks=[(1, 0.25)])[0].score
    two = score_candidates([SEGMENT], audio_peaks=[(1, 0.25), (2, 0.25)])[0].score
    assert two == pytest.approx(min(100.0, one + 1.0))
