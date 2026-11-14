"""Regression tests for malformed transcript input at the scoring boundary."""
import pytest

from app.intelligence.highlights import score_candidates


VALID = {
    "start": 0.0,
    "end": 20.0,
    "text": " ".join(f"word{i}" for i in range(30)),
}


@pytest.mark.parametrize("bad_segment", [
    None, 42, "bad", [], {}, {"start": True, "end": 20, "text": "words"},
    {"start": "0", "end": 20, "text": "words"},
    {"start": 0, "end": "20", "text": "words"},
    {"start": 0, "end": 20, "text": {"invalid": "text"}},
    {"start": float("nan"), "end": 20, "text": "words"},
    {"start": 0, "end": float("inf"), "text": "words"},
])
def test_invalid_segment_is_ignored_without_losing_valid_candidates(bad_segment):
    baseline = score_candidates([VALID])
    assert baseline
    assert score_candidates([bad_segment, VALID]) == baseline


@pytest.mark.parametrize("bad_collection", [None, 123, "not segments", {}, True])
def test_invalid_transcript_collection_returns_no_candidates(bad_collection):
    assert score_candidates(bad_collection) == []


def test_tuple_of_valid_transcript_segments_is_supported():
    assert score_candidates((VALID,)) == score_candidates([VALID])


def test_missing_text_is_treated_as_empty_and_does_not_crash():
    assert score_candidates([{"start": 0, "end": 20}]) == []


@pytest.mark.parametrize("nested_end", [1.0, 10.0, 24.0])
def test_nested_transcript_segment_never_shrinks_candidate_window(nested_end):
    outer = {"start": 0.0, "end": 25.0, "text": " ".join(f"word{i}" for i in range(30))}
    nested = {"start": 0.5, "end": nested_end, "text": "more transcript words"}
    candidates = score_candidates([outer, nested], minimum_seconds=18, maximum_seconds=30)
    assert candidates
    assert all(candidate.end >= 25.0 for candidate in candidates)
    assert all(18 <= candidate.end - candidate.start <= 30 for candidate in candidates)


def test_nested_segments_do_not_create_negative_or_short_windows():
    outer = {"start": 0.0, "end": 30.0, "text": "wow " + " ".join(f"word{i}" for i in range(30))}
    inner = {"start": 2.0, "end": 3.0, "text": "extra words"}
    candidates = score_candidates([outer, inner], minimum_seconds=18, maximum_seconds=35)
    assert candidates
    assert all(candidate.end > candidate.start for candidate in candidates)


def test_nested_segment_does_not_create_false_gap_before_next_segment():
    outer = {"start": 0.0, "end": 25.0, "text": " ".join(f"word{i}" for i in range(30))}
    inner = {"start": 1.0, "end": 2.0, "text": "more words"}
    following = {"start": 27.0, "end": 40.0, "text": " ".join(f"later{i}" for i in range(20))}
    candidates = score_candidates([outer, inner, following], minimum_seconds=18, maximum_seconds=50)
    assert any(candidate.start == 0.0 and candidate.end == 40.0 for candidate in candidates)


@pytest.mark.parametrize("cue,embedded", [
    ("wait", "awaiting"),
    ("wow", "wowzers"),
    ("bro", "broad"),
])
def test_cue_matches_whole_word_not_substring(cue, embedded):
    filler = " ".join(f"word{i}" for i in range(30))
    isolated = {"start": 0, "end": 20, "text": filler + " " + cue}
    inside_word = {"start": 0, "end": 20, "text": filler + " " + embedded}
    cue_candidates = score_candidates([isolated])
    embedded_candidates = score_candidates([inside_word])
    assert cue_candidates and embedded_candidates
    assert cue_candidates[0].score > embedded_candidates[0].score


def test_multiword_cue_requires_word_boundaries():
    filler = " ".join(f"word{i}" for i in range(30))
    isolated = score_candidates([{"start": 0, "end": 20, "text": filler + " no way"}])
    embedded = score_candidates([{"start": 0, "end": 20, "text": filler + " know ways"}])
    assert isolated and embedded
    assert isolated[0].score > embedded[0].score


@pytest.mark.parametrize("field,bad_value", [
    ("minimum_seconds", True), ("minimum_seconds", "18"),
    ("minimum_seconds", None), ("minimum_seconds", float("nan")),
    ("minimum_seconds", float("inf")), ("minimum_seconds", 0),
    ("maximum_seconds", False), ("maximum_seconds", "65"),
    ("maximum_seconds", None), ("maximum_seconds", float("-inf")),
    ("maximum_seconds", 0), ("max_clips", True),
    ("max_clips", 2.0), ("max_clips", "5"),
    ("max_clips", None), ("max_clips", 0), ("max_clips", 6),
])
def test_invalid_scoring_settings_raise_value_error(field, bad_value):
    with pytest.raises(ValueError, match="Invalid duration constraints"):
        score_candidates([VALID], **{field: bad_value})


def test_valid_integer_and_float_durations_remain_supported():
    assert score_candidates([VALID], minimum_seconds=18, maximum_seconds=65.0, max_clips=5)


def test_nested_segments_below_scoring_threshold_are_not_returned():
    """Valid nested windows still need to satisfy the minimum highlight score."""
    outer = {"start": 0.0, "end": 30.0, "text": " ".join(f"word{i}" for i in range(30))}
    inner = {"start": 2.0, "end": 3.0, "text": "extra words"}
    assert score_candidates([outer, inner], minimum_seconds=18, maximum_seconds=35) == []


def test_many_nested_segments_preserve_furthest_coverage_end():
    """Nested captions must not make a connected later segment look disconnected."""
    outer = {"start": 0.0, "end": 25.0,
             "text": "wow !!! " + " ".join(f"word{i}" for i in range(30))}
    nested = [{"start": 1.0 + i * 0.1, "end": 2.0 + i * 0.1,
               "text": "caption"} for i in range(100)]
    following = {"start": 27.0, "end": 40.0,
                 "text": " ".join(f"later{i}" for i in range(20))}
    candidates = score_candidates([outer, *nested, following],
                                  minimum_seconds=18, maximum_seconds=50)
    assert any(c.start == 0.0 and c.end == 40.0 for c in candidates)
