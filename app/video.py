"""Local, authorized input only. Requires ffmpeg on PATH."""
import math
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
            or start_sec < 0 or end_sec <= start_sec):
        raise ValueError("Invalid timestamps")
    if source.resolve() == target.resolve():
        raise ValueError("Input and output must be different files")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Output already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-hide_banner", "-n", "-ss", str(start_sec),
        "-i", str(source), "-t", str(end_sec - start_sec),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(target),
    ]
    # -n prevents a concurrent export from being silently overwritten.
    # Bound stalled encodes; caller removes partial output on failure.
    timeout_seconds = max(120, min(3600, int((end_sec - start_sec) * 30)))
    subprocess.run(command, check=True, timeout=timeout_seconds)
    return str(target)
