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
        ["ffprobe", "-v", "error", "-show_entries",
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
        width = videos[0].get("width")
        height = videos[0].get("height")
        if (not math.isfinite(duration) or duration <= 0
                or type(width) is not int or type(height) is not int
                or width <= 0 or height <= 0):
            raise ValueError("Invalid video metadata")
    except (TypeError, KeyError, AttributeError, OverflowError) as exc:
        raise ValueError("Invalid video metadata") from exc
    return {"duration_seconds": duration, "width": width, "height": height,
            "has_audio": any(isinstance(s, dict) and s.get("codec_type") == "audio"
                             for s in streams)}
