"""Exported clips must not inherit private source metadata or chapters."""
import subprocess
from pathlib import Path

from app import video


def test_export_strips_source_metadata_and_chapters(tmp_path, monkeypatch):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"authorized fixture")
    target = tmp_path / "clip.mp4"
    observed = []

    def fake_run(command, **kwargs):
        observed.append(command)
        Path(command[-1]).write_bytes(b"encoded fixture")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    assert video.render_vertical_clip(source, target, 0, 2) == str(target)
    command = observed[0]
    assert command[command.index("-map_metadata") + 1] == "-1"
    assert command[command.index("-map_chapters") + 1] == "-1"
    assert command.index("-map_metadata") > command.index("-i")
    assert target.read_bytes() == b"encoded fixture"
