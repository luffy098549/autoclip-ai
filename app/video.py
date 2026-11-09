"""Local, authorized input only. Requires ffmpeg on PATH."""
import subprocess
from pathlib import Path


def render_vertical_clip(input_file, output_file, start_sec, end_sec):
    source = Path(input_file)
    target = Path(output_file)
    if not source.is_file():
        raise FileNotFoundError(source)
    if start_sec < 0 or end_sec <= start_sec:
        raise ValueError("Invalid timestamps")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-hide_banner", "-y", "-ss", str(start_sec),
        "-i", str(source), "-t", str(end_sec - start_sec),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(target),
    ]
    subprocess.run(command, check=True)
    return str(target)
