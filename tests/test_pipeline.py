from pathlib import Path
import pytest
from app.pipeline import RightsNotConfirmed, create_local_clip


def test_reject_unapproved_input():
    with pytest.raises(RightsNotConfirmed):
        create_local_clip("fake.mp4", "out.mp4", start=0, end=10)


def test_reject_bad_range_even_if_authorized():
    with pytest.raises(ValueError):
        create_local_clip("fake.mp4", "out.mp4", start=10, end=5, authorized=True)


@pytest.mark.parametrize("start,end", [
    (None, 10), ("not-a-number", 10), (0, None),
    (float("nan"), 10), (0, float("inf")), (float("-inf"), 10),
])
def test_invalid_timestamps_rejected_before_media_inspection(start, end):
    with pytest.raises(ValueError, match="Invalid clip timestamps"):
        create_local_clip("missing.mp4", "out.mp4", start=start, end=end, authorized=True)


def test_numeric_string_timestamps_are_normalized(monkeypatch, tmp_path):
    from app import pipeline
    observed = {}

    monkeypatch.setattr(pipeline, "inspect_video", lambda _: {
        "duration": 30.0, "has_audio": True
    })

    def fake_render(source, target, start, end):
        observed["range"] = (start, end)
        return str(target)

    monkeypatch.setattr(pipeline, "render_vertical_clip", fake_render)
    monkeypatch.setattr(pipeline, "validate_render", lambda _: {"duration": 10})
    create_local_clip("owned.mp4", tmp_path / "out.mp4",
                      start="1.5", end="11.5", authorized=True)
    assert observed["range"] == (1.5, 11.5)
