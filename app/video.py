"""Local, authorized input only. Requires ffmpeg on PATH."""
import math
import os
import tempfile
import subprocess
from pathlib import Path


def render_vertical_clip(input_file, output_file, start_sec, end_sec):
    source = Path(input_file)
    target = Path(output_file)
    if not source.is_file():
        raise FileNotFoundError(source)
    if (isinstance(start_sec, bool) or isinstance(end_sec, bool)
            or not isinstance(start_sec, (int, float))
            or not isinstance(end_sec, (int, float))
            or not math.isfinite(start_sec) or not math.isfinite(end_sec)
            or start_sec < 0 or end_sec <= start_sec
            or end_sec - start_sec > 300):
        raise ValueError("Invalid timestamps")
    if source.resolve() == target.resolve():
        raise ValueError("Input and output must be different files")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Output already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Each export owns its temporary file. Publish via hard link only after success.
    fd, temporary_name = tempfile.mkstemp(prefix=".autoclip-", suffix=".mp4", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    command = [
        "ffmpeg", "-hide_banner", "-nostdin", "-y", "-ss", str(start_sec),
        "-protocol_whitelist", "file", "-i", str(source), "-t", str(end_sec - start_sec),
        "-map", "0:V:0", "-map", "0:a:0?",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart", str(temporary),
    ]
    # Bound stalled encodes; temporary output is always removed on failure.
    timeout_seconds = max(120, min(3600, int(min(end_sec - start_sec, 120) * 30)))
    try:
        subprocess.run(command, check=True, timeout=timeout_seconds)
        # A zero-byte output is never a valid export, even when FFmpeg exits 0.
        if temporary.stat().st_size == 0:
            raise RuntimeError("FFmpeg produced an empty output")
        # os.link fails if another worker has already published this name.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(target)
