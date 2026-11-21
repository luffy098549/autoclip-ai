"""Media probing rejects corrupt metadata before editing authorized sources."""
import json
import subprocess

import pytest

from app import quality


def _probe(tmp_path, monkeypatch, *, duration="12.5", width=1920, height=1080):
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(quality.shutil, "which", lambda name: "/usr/bin/ffprobe")

    def fake_run(command, **kwargs):
        assert kwargs["timeout"] == 60
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps({
                "format": {"duration": duration},
                "streams": [
                    {"codec_type": "video", "width": width, "height": height},
                    {"codec_type": "audio"},
                ],
            }),
        )

    monkeypatch.setattr(quality.subprocess, "run", fake_run)
    return source


@pytest.mark.parametrize("duration", ["NaN", "Infinity", "-Infinity", "0", "-1", "not-a-number", {}, None])
def test_reject_bad_duration(tmp_path, monkeypatch, duration):
    source = _probe(tmp_path, monkeypatch, duration=duration)
    with pytest.raises(quality.MediaValidationError):
        quality.inspect_video(source)


@pytest.mark.parametrize("width,height", [(0, 1080), (1920, 0), (-1, 1080), ("bad", 1080), (None, 1080), (float("inf"), 1080)])
def test_reject_bad_dimensions(tmp_path, monkeypatch, width, height):
    source = _probe(tmp_path, monkeypatch, width=width, height=height)
    with pytest.raises(quality.MediaValidationError):
        quality.inspect_video(source)


def test_valid_probe_metadata(tmp_path, monkeypatch):
    source = _probe(tmp_path, monkeypatch)
    info = quality.inspect_video(source)
    assert info == {"duration": 12.5, "width": 1920, "height": 1080, "has_audio": True}


@pytest.mark.parametrize("minimum", [float("nan"), float("inf"), -1, True, "1"])
def test_invalid_minimum_rejected_before_probe(monkeypatch, minimum):
    monkeypatch.setattr(quality, "inspect_video", lambda path: pytest.fail("Probe must not run"))
    with pytest.raises(ValueError):
        quality.validate_render("unused.mp4", expected_min_seconds=minimum)


@pytest.mark.parametrize("payload", [
    "not json", "null", "[]", "42", "{}",
    '{"streams": null, "format": {"duration": 5}}',
    '{"streams": {}, "format": {"duration": 5}}',
    '{"streams": [null], "format": {"duration": 5}}',
    '{"streams": [{"codec_type": "video", "width": 100, "height": 100}], "format": []}',
])
def test_malformed_ffprobe_report_is_media_error(tmp_path, monkeypatch, payload):
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(quality.shutil, "which", lambda name: "/usr/bin/ffprobe")
    monkeypatch.setattr(
        quality.subprocess, "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, stdout=payload),
    )
    with pytest.raises(quality.MediaValidationError):
        quality.inspect_video(source)


def test_stream_duration_fallback_for_valid_container(tmp_path, monkeypatch):
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(quality.shutil, "which", lambda name: "/usr/bin/ffprobe")
    payload = {
        "format": {},
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "duration": "8.25"},
            {"codec_type": "audio"},
        ],
    }
    monkeypatch.setattr(quality.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=json.dumps(payload)))
    assert quality.inspect_video(source)["duration"] == 8.25


def test_cover_art_does_not_replace_real_video_stream(tmp_path, monkeypatch):
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(quality.shutil, "which", lambda name: "/usr/bin/ffprobe")
    payload = {
        "format": {"duration": "7"},
        "streams": [
            {"codec_type": "video", "width": 500, "height": 500,
             "disposition": {"attached_pic": 1}},
            {"codec_type": "video", "width": 1080, "height": 1920},
            {"codec_type": "audio"},
        ],
    }
    monkeypatch.setattr(quality.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=json.dumps(payload)))
    assert quality.validate_render(source)["width"] == 1080


def test_cover_art_alone_is_not_video(tmp_path, monkeypatch):
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(quality.shutil, "which", lambda name: "/usr/bin/ffprobe")
    payload = {"format": {"duration": "7"}, "streams": [
        {"codec_type": "video", "width": 500, "height": 500,
         "disposition": {"attached_pic": 1}},
    ]}
    monkeypatch.setattr(quality.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=json.dumps(payload)))
    with pytest.raises(quality.MediaValidationError, match="No video stream"):
        quality.inspect_video(source)


@pytest.mark.parametrize("container_duration", ["N/A", "0", "-1", "NaN", "Infinity", None])
def test_invalid_container_duration_uses_valid_stream_duration(tmp_path, monkeypatch, container_duration):
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(quality.shutil, "which", lambda name: "/usr/bin/ffprobe")
    payload = {
        "format": {"duration": container_duration},
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "duration": "9.5"},
            {"codec_type": "audio"},
        ],
    }
    monkeypatch.setattr(quality.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=json.dumps(payload)))
    assert quality.inspect_video(source)["duration"] == 9.5


@pytest.mark.parametrize("container_duration", ["bad-value", {}, [], "", "  ", True])
def test_malformed_container_duration_recovers_from_stream(tmp_path, monkeypatch, container_duration):
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(quality.shutil, "which", lambda name: "/usr/bin/ffprobe")
    payload = {
        "format": {"duration": container_duration},
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "duration": "11.25"},
            {"codec_type": "audio"},
        ],
    }
    monkeypatch.setattr(quality.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=json.dumps(payload)))
    assert quality.inspect_video(source)["duration"] == 11.25


def test_invalid_container_and_stream_durations_are_rejected(tmp_path, monkeypatch):
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(quality.shutil, "which", lambda name: "/usr/bin/ffprobe")
    payload = {"format": {"duration": "broken"}, "streams": [
        {"codec_type": "video", "width": 1080, "height": 1920, "duration": "also-broken"}
    ]}
    monkeypatch.setattr(quality.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=json.dumps(payload)))
    with pytest.raises(quality.MediaValidationError, match="positive duration"):
        quality.inspect_video(source)
