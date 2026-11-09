"""Regression tests for daylight-saving transitions in the private planning calendar."""
from datetime import datetime, timezone

import pytest

from app.routes.planning import _parse_ny_time


def test_spring_forward_nonexistent_local_time_is_rejected():
    with pytest.raises(ValueError, match="no existe"):
        _parse_ny_time("2027-03-14T02:30")


def test_fall_back_ambiguous_local_time_is_rejected():
    with pytest.raises(ValueError, match="ambigua"):
        _parse_ny_time("2027-11-07T01:30")


def test_unambiguous_local_time_converts_to_utc():
    assert _parse_ny_time("2027-11-07T03:30") == datetime(
        2027, 11, 7, 8, 30, tzinfo=timezone.utc
    )
