"""Media validation for a local, authorized video source."""
import json
import math
import shutil
import subprocess
from pathlib import Path


class MediaValidationError(ValueError):
    pass


def inspect_video(path):
    media = Path(path)
    if not media.is_file():
        raise MediaValidationError(f"File does not exist: {media}")
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe must be installed")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(media)],
        check=True, capture_output=True, text=True, timeout=60,
        stdin=subprocess.DEVNULL,
    )
    try:
        report = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise MediaValidationError("Invalid ffprobe JSON") from exc
    if not isinstance(report, dict):
        raise MediaValidationError("Invalid ffprobe report")
    streams = report.get("streams")
    if not isinstance(streams, list) or any(not isinstance(s, dict) for s in streams):
        raise MediaValidationError("Invalid ffprobe streams")
    video = next(
        (
            stream for stream in streams
            if stream.get("codec_type") == "video"
            and not (
                isinstance(stream.get("disposition"), dict)
                and stream["disposition"].get("attached_pic")
            )
        ),
        None,
    )
    if video is None:
        raise MediaValidationError("No video stream found")
    fmt = report.get("format")
    if not isinstance(fmt, dict):
        raise MediaValidationError("Invalid ffprobe format")
    try:
        container_duration = fmt.get("duration")
        stream_duration = video.get("duration")
        def positive_duration(value):
            if isinstance(value, bool):
                return 0.0
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError):
                return 0.0
            return number if math.isfinite(number) and number > 0 else 0.0

        duration = positive_duration(container_duration) or positive_duration(stream_duration)
        width = video.get("width")
        height = video.get("height")
        if (type(width) is not int or type(height) is not int):
            raise MediaValidationError("Invalid video dimensions")
    except (TypeError, ValueError, OverflowError) as exc:
        raise MediaValidationError("Invalid video metadata") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise MediaValidationError("Cannot determine a positive duration")
    if width <= 0 or height <= 0:
        raise MediaValidationError("Invalid video dimensions")
    return {
        "duration": duration,
        "width": width,
        "height": height,
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def validate_render(path, expected_min_seconds=1):
    if (isinstance(expected_min_seconds, bool)
            or not isinstance(expected_min_seconds, (int, float))
            or not math.isfinite(expected_min_seconds)
            or expected_min_seconds < 0):
        raise ValueError("Invalid minimum duration")
    info = inspect_video(path)
    if info["width"] != 1080 or info["height"] != 1920:
        raise MediaValidationError("Export must be 1080x1920")
    if info["duration"] < expected_min_seconds:
        raise MediaValidationError("Export is too short")
    if not info["has_audio"]:
        raise MediaValidationError("Export is missing audio")
    return info
