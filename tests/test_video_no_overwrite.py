"""FFmpeg export must never silently overwrite another clip."""
import subprocess
import pytest
from app import video


def test_ffmpeg_uses_no_overwrite_mode(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"owned")
    destination = tmp_path / "clip.mp4"
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        assert kwargs["check"] is True
        assert "-n" in command
        assert "-y" not in command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    assert video.render_vertical_clip(source, destination, 0, 3) == str(destination)
    assert len(commands) == 1


def test_ffmpeg_failure_is_propagated(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"owned")

    def fail(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(video.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        video.render_vertical_clip(source, tmp_path / "clip.mp4", 0, 3)
