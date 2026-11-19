"""Inspect locally imported, authorized media without decoding full content."""
import json
import math
import subprocess
from pathlib import Path


def inspect_local_video(path):
    """Return validated video metadata for preview and clip-range editing."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-protocol_whitelist", "file",
         "-show_entries",
         "format=duration:stream=codec_type,width,height,disposition",
         "-of", "json", str(source)],
        check=True, capture_output=True, text=True, timeout=30,
        stdin=subprocess.DEVNULL,
    )
    try:
        data = json.loads(result.stdout)
        if not isinstance(data, dict):
            raise ValueError("Invalid video metadata")
        streams = data.get("streams", [])
        if not isinstance(streams, list):
            raise ValueError("Invalid video metadata")
        videos = []
        for stream in streams:
            if not isinstance(stream, dict) or stream.get("codec_type") != "video":
                continue
            disposition = stream.get("disposition")
            if disposition is not None and not isinstance(disposition, dict):
                raise ValueError("Invalid video metadata")
            if not (disposition or {}).get("attached_pic", 0):
                videos.append(stream)
        if not videos:
            raise ValueError("Media has no video stream")
        fmt = data.get("format")
        if not isinstance(fmt, dict):
            raise ValueError("Invalid video metadata")
        duration = float(fmt.get("duration", 0))
        # Prefer a valid picture stream when a container has multiple video tracks.
        usable = [s for s in videos if type(s.get("width")) is int
                  and type(s.get("height")) is int
                  and s["width"] > 0 and s["height"] > 0]
        if not usable:
            raise ValueError("Invalid video metadata")
        width = usable[0]["width"]
        height = usable[0]["height"]
        if (not math.isfinite(duration) or duration <= 0
                or type(width) is not int or type(height) is not int
                or width <= 0 or height <= 0):
            raise ValueError("Invalid video metadata")
    except (TypeError, KeyError, AttributeError, OverflowError) as exc:
        raise ValueError("Invalid video metadata") from exc
    return {"duration_seconds": duration, "width": width, "height": height,
            "has_audio": any(isinstance(s, dict) and s.get("codec_type") == "audio"
                             for s in streams)}


def validate_clip_range(metadata, start_seconds, end_seconds, *, max_duration_seconds=300):
    """Validate a requested clip against inspected media before scheduling FFmpeg."""
    if not isinstance(metadata, dict):
        raise ValueError("Invalid video metadata")
    # bool is an int subclass, but never a meaningful timestamp or duration.
    if (isinstance(start_seconds, bool) or isinstance(end_seconds, bool)
            or isinstance(max_duration_seconds, bool)
            or isinstance(metadata.get("duration_seconds"), bool)):
        raise ValueError("Invalid clip range")
    try:
        duration = float(metadata["duration_seconds"])
        start = float(start_seconds)
        end = float(end_seconds)
        limit = float(max_duration_seconds)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Invalid clip range") from exc
    if (not all(math.isfinite(v) for v in (duration, start, end, limit))
            or duration <= 0 or limit <= 0 or start < 0 or end <= start
            or end > duration + 1e-6 or end - start > limit):
        raise ValueError("Invalid clip range")
    return {"start_seconds": start, "end_seconds": end,
            "duration_seconds": end - start}
