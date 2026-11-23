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


@pytest.mark.parametrize("index", [1, 2])
def test_batch_rejects_source_destination_collision_before_any_encode(fake_exports, index):
    calls, folder = fake_exports
    source = folder / f"clip-{index:02d}.mp4"
    source.write_bytes(b"authorized source")
    with pytest.raises(ValueError, match="Source and export destination"):
        pipeline.create_local_clip_batch(
            source, folder,
            [{"start": 0, "end": 10}, {"start": 20, "end": 30}],
            authorized=True,
        )
    assert calls == []
    assert source.read_bytes() == b"authorized source"
    assert not (folder / f"clip-{3-index:02d}.mp4").exists()


def test_batch_rejects_alias_to_source_before_encoding(fake_exports):
    calls, folder = fake_exports
    source = folder / "clip-02.mp4"
    source.write_bytes(b"authorized source")
    alias_folder = folder / "subfolder" / ".."
    (folder / "subfolder").mkdir()
    with pytest.raises(ValueError, match="Source and export destination"):
        pipeline.create_local_clip_batch(
            source, alias_folder,
            [{"start": 0, "end": 10}, {"start": 20, "end": 30}],
            authorized=True,
        )
    assert calls == []


@pytest.mark.parametrize("ranges", [
    [{"start": 0, "end": 10, "extra": 1}],
    [{"start": float("nan"), "end": 10}],
    [{"start": 0, "end": float("inf")}],
    [{"start": True, "end": 10}],
    [{"start": -1, "end": 10}],
    [{"start": 10, "end": 10}],
    [{"start": 0, "end": 10}, {"start": "bad", "end": 20}],
])
def test_batch_malformed_ranges_rejected_before_probe(tmp_path, monkeypatch, ranges):
    monkeypatch.setattr(pipeline, "inspect_video",
                        lambda _: pytest.fail("invalid batch must not invoke ffprobe"))
    monkeypatch.setattr(pipeline, "render_vertical_clip",
                        lambda *args: pytest.fail("invalid batch must not encode"))
    with pytest.raises(ValueError):
        pipeline.create_local_clip_batch("authorized.mp4", tmp_path, ranges,
                                         authorized=True)


def test_batch_rejects_symlink_export_directory_before_render(fake_exports):
    calls, folder = fake_exports
    actual = folder / "actual"
    actual.mkdir()
    alias = folder / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        pipeline.create_local_clip_batch(
            "authorized.mp4", alias, [{"start": 0, "end": 10}],
            authorized=True,
        )
    assert calls == []
    assert list(actual.iterdir()) == []


def test_batch_rejects_file_as_export_directory_before_render(fake_exports):
    calls, folder = fake_exports
    target = folder / "not-a-directory"
    target.write_text("preserve")
    with pytest.raises(NotADirectoryError):
        pipeline.create_local_clip_batch(
            "authorized.mp4", target, [{"start": 0, "end": 10}],
            authorized=True,
        )
    assert calls == []
    assert target.read_text() == "preserve"


def test_batch_rejects_symlink_parent_before_render(fake_exports):
    calls, folder = fake_exports
    real_parent = folder / "real-parent"
    real_parent.mkdir()
    alias_parent = folder / "alias-parent"
    alias_parent.symlink_to(real_parent, target_is_directory=True)
    destination = alias_parent / "new-clips"
    with pytest.raises(ValueError, match="symlink"):
        pipeline.create_local_clip_batch(
            "authorized.mp4", destination, [{"start": 0, "end": 10}],
            authorized=True,
        )
    assert calls == []
    assert not (real_parent / "new-clips").exists()


def test_batch_allows_regular_nested_output_directory(fake_exports):
    calls, folder = fake_exports
    destination = folder / "regular-parent" / "new-clips"
    result = pipeline.create_local_clip_batch(
        "authorized.mp4", destination, [{"start": 0, "end": 10}],
        authorized=True,
    )
    assert calls == [(0, 10)]
    assert len(result["clips"]) == 1
    assert (destination / "clip-01.mp4").exists()
