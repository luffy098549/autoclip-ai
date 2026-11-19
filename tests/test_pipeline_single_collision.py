"""Single-clip export must never overwrite its own source."""
import pytest
from app import pipeline


def test_single_clip_source_destination_collision(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    calls = []
    monkeypatch.setattr(pipeline, "inspect_video", lambda _: calls.append("probe"))
    monkeypatch.setattr(pipeline, "render_vertical_clip", lambda *a: calls.append("render"))
    with pytest.raises(ValueError, match="Source and export destination"):
        pipeline.create_local_clip(source, source, start=0, end=10, authorized=True)
    assert calls == []
    assert source.read_bytes() == b"original"


def test_single_clip_source_alias_collision(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    (tmp_path / "sub").mkdir()
    monkeypatch.setattr(pipeline, "inspect_video", lambda _: pytest.fail("must reject before probing"))
    with pytest.raises(ValueError, match="Source and export destination"):
        pipeline.create_local_clip(source, tmp_path / "sub" / ".." / "source.mp4",
                                   start=0, end=10, authorized=True)
    assert source.read_bytes() == b"original"
