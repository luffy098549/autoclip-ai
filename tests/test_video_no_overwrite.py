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


@pytest.mark.parametrize("start,end", [
    (float("nan"), 2), (0, float("inf")), (True, 2),
    (0, False), ("0", 2), (0, "2"), (-1, 2), (3, 2),
])
def test_reject_invalid_timestamps_before_ffmpeg(tmp_path, monkeypatch, start, end):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"owned")

    def unexpected(*args, **kwargs):
        pytest.fail("FFmpeg must not run for invalid timestamps")

    monkeypatch.setattr(video.subprocess, "run", unexpected)
    with pytest.raises(ValueError):
        video.render_vertical_clip(source, tmp_path / "out.mp4", start, end)


def test_reject_existing_output_without_running_ffmpeg(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"owned")
    destination = tmp_path / "out.mp4"
    destination.write_bytes(b"keep")
    monkeypatch.setattr(video.subprocess, "run", lambda *a, **kw: pytest.fail("Unexpected FFmpeg"))
    with pytest.raises(FileExistsError):
        video.render_vertical_clip(source, destination, 0, 2)
    assert destination.read_bytes() == b"keep"


def test_reject_same_input_output_and_symlink(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"owned")
    monkeypatch.setattr(video.subprocess, "run", lambda *a, **kw: pytest.fail("Unexpected FFmpeg"))
    with pytest.raises(ValueError):
        video.render_vertical_clip(source, source, 0, 2)
    alias = tmp_path / "alias.mp4"
    alias.symlink_to(source)
    with pytest.raises(ValueError):
        video.render_vertical_clip(source, alias, 0, 2)


def test_reject_dangling_symlink_output(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"owned")
    alias = tmp_path / "alias.mp4"
    alias.symlink_to(tmp_path / "missing.mp4")
    monkeypatch.setattr(video.subprocess, "run", lambda *a, **kw: pytest.fail("Unexpected FFmpeg"))
    with pytest.raises(FileExistsError):
        video.render_vertical_clip(source, alias, 0, 2)


@pytest.mark.parametrize("start,end,expected", [
    (0, 2, 120),
    (0, 20, 600),
    (0, 500, 3600),
])
def test_export_has_bounded_timeout(tmp_path, monkeypatch, start, end, expected):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"authorized fixture")
    seen = []

    def fake_run(command, **kwargs):
        seen.append(kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    video.render_vertical_clip(source, tmp_path / "out.mp4", start, end)
    assert seen == [expected]


def test_ffmpeg_timeout_propagates_to_cleanup_caller(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"authorized fixture")

    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(video.subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        video.render_vertical_clip(source, tmp_path / "out.mp4", 0, 3)


def test_ffmpeg_noninteractive_and_explicit_stream_selection(tmp_path, monkeypatch):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"fixture")
    observed = []

    def fake_run(command, **kwargs):
        observed.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    video.render_vertical_clip(source, tmp_path / "clip.mp4", 0, 2)
    command = observed[0]
    assert "-nostdin" in command
    maps = [command[i + 1] for i, item in enumerate(command[:-1]) if item == "-map"]
    assert maps == ["0:v:0", "0:a:0?"]
    assert command.index("-nostdin") < command.index("-i")
