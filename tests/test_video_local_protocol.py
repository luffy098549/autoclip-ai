"""FFmpeg input isolation and successful local export regressions."""
import subprocess
from pathlib import Path

import pytest

from app import video


def test_ffmpeg_restricts_input_protocol_and_disables_stdin(tmp_path, monkeypatch):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"authorized")
    output = tmp_path / "clip.mp4"
    seen = []

    def fake_run(command, **kwargs):
        seen.extend(command)
        assert command[command.index("-protocol_whitelist") + 1] == "file"
        assert command.index("-protocol_whitelist") < command.index("-i")
        assert "-nostdin" in command
        Path(command[-1]).write_bytes(b"encoded")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    assert video.render_vertical_clip(source, output, 0, 2) == str(output)
    assert output.read_bytes() == b"encoded"
    assert seen.count("-protocol_whitelist") == 1


@pytest.mark.parametrize("start,end", [(True, 2), (0, False), (-1, 2), (2, 2), (2, 1), (float("nan"), 3), (0, 301), (0, float("inf"))])
def test_invalid_ranges_do_not_start_encoder(tmp_path, monkeypatch, start, end):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"authorized")
    def forbidden(*args, **kwargs):
        raise AssertionError("Encoder should not be invoked")
    monkeypatch.setattr(video.subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="Invalid timestamps"):
        video.render_vertical_clip(source, tmp_path / "clip.mp4", start, end)


def test_maximum_allowed_export_duration(tmp_path, monkeypatch):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"authorized")
    output = tmp_path / "clip.mp4"

    def fake_run(command, **kwargs):
        Path(command[-1]).write_bytes(b"encoded")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    assert video.render_vertical_clip(source, output, 0, 300) == str(output)


def test_failed_export_cleans_temporary_file(tmp_path, monkeypatch):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"authorized")
    output = tmp_path / "clip.mp4"

    def fake_run(command, **kwargs):
        Path(command[-1]).write_bytes(b"partial")
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        video.render_vertical_clip(source, output, 0, 3)
    assert not output.exists()
    assert not list(tmp_path.glob(".autoclip-*.mp4"))


def test_empty_export_is_rejected_and_cleaned(tmp_path, monkeypatch):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"authorized")
    output = tmp_path / "clip.mp4"

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="empty output"):
        video.render_vertical_clip(source, output, 0, 3)
    assert not output.exists()
    assert not list(tmp_path.glob(".autoclip-*.mp4"))
