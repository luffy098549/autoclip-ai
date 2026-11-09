"""Media validation for a local, authorized video source."""
import json
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
    )
    report = json.loads(result.stdout)
    streams = report.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise MediaValidationError("No video stream found")
    duration = float(report.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise MediaValidationError("Cannot determine a positive duration")
    return {
        "duration": duration,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def validate_render(path, expected_min_seconds=1):
    info = inspect_video(path)
    if info["width"] != 1080 or info["height"] != 1920:
        raise MediaValidationError("Export must be 1080x1920")
    if info["duration"] < expected_min_seconds:
        raise MediaValidationError("Export is too short")
    if not info["has_audio"]:
        raise MediaValidationError("Export is missing audio")
    return info
