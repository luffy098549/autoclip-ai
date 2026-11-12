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
    (float("nan"), 5), (0, float("nan")),
    (float("inf"), 5), (0, float("inf")),
    (-float("inf"), 5), (0, -float("inf")),
    ("0", 5), (0, "5"), (True, 5), (0, False),
])
def test_reject_invalid_timestamps_before_media_probe(monkeypatch, tmp_path, start, end):
    def unexpected_probe(_source):
        pytest.fail("invalid timestamps must not probe the source")
    monkeypatch.setattr("app.pipeline.inspect_video", unexpected_probe)
    with pytest.raises(ValueError, match="Invalid clip timestamps"):
        create_local_clip("fake.mp4", tmp_path / "out.mp4",
                          start=start, end=end, authorized=True)


@pytest.mark.parametrize("duration", [float("nan"), float("inf"), -1, 0, "12"])
def test_reject_invalid_probe_duration(monkeypatch, tmp_path, duration):
    monkeypatch.setattr("app.pipeline.inspect_video",
                        lambda _source: {"duration": duration, "has_audio": True})
    def unexpected_render(*args, **kwargs):
        pytest.fail("invalid source duration must not be rendered")
    monkeypatch.setattr("app.pipeline.render_vertical_clip", unexpected_render)
    with pytest.raises(ValueError, match="Invalid source duration"):
        create_local_clip("fake.mp4", tmp_path / "out.mp4",
                          start=0, end=5, authorized=True)


def test_failed_render_removes_partial_output(monkeypatch, tmp_path):
    output = tmp_path / "out.mp4"
    monkeypatch.setattr("app.pipeline.inspect_video",
                        lambda _source: {"duration": 20, "has_audio": True})
    def partial_render(_source, destination, _start, _end):
        Path(destination).write_bytes(b"incomplete")
        raise RuntimeError("ffmpeg failed")
    monkeypatch.setattr("app.pipeline.render_vertical_clip", partial_render)
    with pytest.raises(RuntimeError, match="ffmpeg failed"):
        create_local_clip("fake.mp4", output, start=0, end=5, authorized=True)
    assert not output.exists()


def test_existing_export_is_never_deleted_or_overwritten(monkeypatch, tmp_path):
    output = tmp_path / "out.mp4"
    output.write_bytes(b"existing")
    monkeypatch.setattr("app.pipeline.inspect_video",
                        lambda _source: {"duration": 20, "has_audio": True})
    with pytest.raises(FileExistsError):
        create_local_clip("fake.mp4", output, start=0, end=5, authorized=True)
    assert output.read_bytes() == b"existing"
