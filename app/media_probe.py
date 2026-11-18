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
         "format=duration:stream=codec_type,width,height", "-of", "json", str(source)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    data = json.loads(result.stdout)
    videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    if not videos:
        raise ValueError("Media has no video stream")
    duration = float(data.get("format", {}).get("duration", 0))
    width = videos[0].get("width")
    height = videos[0].get("height")
    if not math.isfinite(duration) or duration <= 0 or not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError("Invalid video metadata")
    return {"duration_seconds": duration, "width": width, "height": height,
            "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", []))}
