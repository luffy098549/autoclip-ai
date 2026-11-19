"""Regression coverage for bounded local multi-clip export."""
import pytest
from app import pipeline


@pytest.fixture
def fake_exports(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(pipeline, "inspect_video", lambda source: {
        "duration": 120, "has_audio": True, "width": 1920, "height": 1080
    })
    def render(source, target, start, end):
        calls.append((start, end))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake mp4")
        return str(target)
    monkeypatch.setattr(pipeline, "render_vertical_clip", render)
    monkeypatch.setattr(pipeline, "validate_render", lambda path: {"duration": 10})
    return calls, tmp_path


def test_batch_exports_multiple_clips(fake_exports):
    calls, folder = fake_exports
    result = pipeline.create_local_clip_batch(
        "authorized.mp4", folder, [{"start": 0, "end": 10}, {"start": 20, "end": 30}],
        authorized=True
    )
    assert calls == [(0, 10), (20, 30)]
    assert len(result["clips"]) == 2
    assert (folder / "clip-01.mp4").exists()
    assert (folder / "clip-02.mp4").exists()


@pytest.mark.parametrize("ranges", [
    [], [{"start": 0, "end": 1}] * 6,
    [{"start": 0, "end": 10}, {"start": 0.0, "end": 10.0}],
    [{"start": 0, "end": 121}],
    [{"start": True, "end": 10}],
    [{"start": 0, "end": 10, "unexpected": 1}],
])
def test_invalid_batch_never_starts_encoder(fake_exports, ranges):
    calls, folder = fake_exports
    with pytest.raises(ValueError):
        pipeline.create_local_clip_batch("authorized.mp4", folder, ranges, authorized=True)
    assert calls == []


def test_batch_requires_rights(fake_exports):
    calls, folder = fake_exports
    with pytest.raises(pipeline.RightsNotConfirmed):
        pipeline.create_local_clip_batch("source.mp4", folder, [{"start": 0, "end": 10}])
    assert calls == []


def test_batch_refuses_existing_output_before_encoding(fake_exports):
    calls, folder = fake_exports
    (folder / "clip-02.mp4").write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        pipeline.create_local_clip_batch("source.mp4", folder,
            [{"start": 0, "end": 10}, {"start": 20, "end": 30}], authorized=True)
    assert calls == []
