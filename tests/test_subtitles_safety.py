"""Regression tests for SRT output used by clip export and caption burning."""
import math
import pytest
from app.services.subtitles import build_srt, srt_timestamp


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf"), -1, True, None, "invalid"])
def test_srt_timestamp_rejects_invalid_values(invalid):
    with pytest.raises(ValueError):
        srt_timestamp(invalid)


def test_srt_timestamp_rounding():
    assert srt_timestamp(3661.125) == "01:01:01,125"


def test_empty_cues_do_not_create_numbering_gaps():
    result = build_srt([
        {"start": 0, "end": 1, "text": "first"},
        {"start": 1, "end": 2, "text": "  "},
        {"start": 2, "end": 3, "text": "third"},
    ])
    assert result == ("1\n00:00:00,000 --> 00:00:01,000\nfirst\n\n"
                      "2\n00:00:02,000 --> 00:00:03,000\nthird\n")


@pytest.mark.parametrize("start,end", [(float("nan"), 3), (0, float("inf")), (-1, 2), (3, 3), (4, 3)])
def test_build_srt_rejects_invalid_intervals(start, end):
    with pytest.raises(ValueError):
        build_srt([{"start": start, "end": end, "text": "test"}])


def test_build_srt_strips_null_bytes():
    assert "hi there" in build_srt([{"start": 0, "end": 1, "text": "hi\x00 there"}])


def test_timestamp_rejects_overflow_when_converting_to_milliseconds():
    with pytest.raises(ValueError, match="supported range"):
        srt_timestamp(1e308)


@pytest.mark.parametrize("field", ["start", "end"])
def test_build_srt_rejects_boolean_timestamps(field):
    segment = {"start": 0, "end": 2, "text": "hello"}
    segment[field] = True
    with pytest.raises(ValueError, match="finite nonnegative"):
        build_srt([segment])


def test_build_srt_rejects_oversized_timestamps():
    with pytest.raises(ValueError, match="supported range"):
        build_srt([{"start": 0, "end": 1e308, "text": "hello"}])
