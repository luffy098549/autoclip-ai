"""Regression tests for authorized vertical clip rendering and cleanup."""
import pytest

from app import pipeline


@pytest.fixture
def video_stubs(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "inspect_video", lambda _: {"duration": 30, "has_audio": True})
    monkeypatch.setattr(pipeline, "render_vertical_clip",
                        lambda source, target, start, end: calls.append((start, end)) or str(target))
    monkeypatch.setattr(pipeline, "validate_render", lambda _: {"valid": True})
    return calls


@pytest.mark.parametrize("start,end", [
    (float("nan"), 5), (0, float("inf")), (float("-inf"), 5),
    (True, 5), (0, False), ("0", 5), (0, "5"),
    (5, 5), (6, 5), (-1, 5),
])
def test_invalid_timestamps_rejected_before_probe(tmp_path, monkeypatch, start, end):
    monkeypatch.setattr(pipeline, "inspect_video",
                        lambda _: pytest.fail("probe must not run for invalid timestamps"))
    with pytest.raises(ValueError, match="Invalid clip timestamps"):
        pipeline.create_local_clip("owned.mp4", tmp_path / "clip.mp4",
                                   start=start, end=end, authorized=True)


def test_authorization_required(tmp_path, video_stubs):
    with pytest.raises(pipeline.RightsNotConfirmed):
        pipeline.create_local_clip("owned.mp4", tmp_path / "clip.mp4",
                                   start=0, end=5)
    assert video_stubs == []


def test_successful_render(tmp_path, video_stubs):
    target = tmp_path / "clip.mp4"
    result = pipeline.create_local_clip("owned.mp4", target,
                                        start=2, end=6, authorized=True)
    assert result["path"] == str(target)
    assert video_stubs == [(2, 6)]


def test_render_failure_removes_partial_file(tmp_path, monkeypatch, video_stubs):
    target = tmp_path / "clip.mp4"

    def fail_render(*args):
        target.write_bytes(b"partial mp4")
        raise RuntimeError("ffmpeg failed")

    monkeypatch.setattr(pipeline, "render_vertical_clip", fail_render)
    with pytest.raises(RuntimeError, match="ffmpeg failed"):
        pipeline.create_local_clip("owned.mp4", target,
                                   start=0, end=5, authorized=True)
    assert not target.exists()


def test_validation_failure_removes_partial_file(tmp_path, monkeypatch, video_stubs):
    target = tmp_path / "clip.mp4"

    def render(*args):
        target.write_bytes(b"invalid mp4")
        return str(target)

    monkeypatch.setattr(pipeline, "render_vertical_clip", render)
    monkeypatch.setattr(pipeline, "validate_render",
                        lambda _: (_ for _ in ()).throw(ValueError("invalid output")))
    with pytest.raises(ValueError, match="invalid output"):
        pipeline.create_local_clip("owned.mp4", target,
                                   start=0, end=5, authorized=True)
    assert not target.exists()


def test_existing_export_never_overwritten_or_deleted(tmp_path, monkeypatch, video_stubs):
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"keep me")
    with pytest.raises(FileExistsError):
        pipeline.create_local_clip("owned.mp4", target,
                                   start=0, end=5, authorized=True)
    assert target.read_bytes() == b"keep me"
