from pathlib import Path
import pytest
from app.pipeline import RightsNotConfirmed, create_local_clip


def test_reject_unapproved_input():
    with pytest.raises(RightsNotConfirmed):
        create_local_clip("fake.mp4", "out.mp4", start=0, end=10)


def test_reject_bad_range_even_if_authorized():
    with pytest.raises(ValueError):
        create_local_clip("fake.mp4", "out.mp4", start=10, end=5, authorized=True)
