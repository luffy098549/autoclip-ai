"""Burn an authorized subtitle file onto an exported vertical clip with FFmpeg."""
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4
from ..quality import validate_render


def burn_subtitles(source_video, srt_file, output_video):
    source = Path(source_video).resolve()
    subtitles = Path(srt_file).resolve()
    output = Path(output_video).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if not subtitles.is_file():
        raise FileNotFoundError(subtitles)
    if source == output:
        raise ValueError("Output path must differ from the original")
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    local_srt = source.parent / f".autoclip-sub-{uuid4().hex}.srt"
    try:
        shutil.copyfile(subtitles, local_srt)
        # Controlled, generated SRT filename in the video's directory avoids
        # FFmpeg's cross-platform filter path/colon escaping problems.
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
            "-i", source.name, "-vf", f"subtitles={local_srt.name}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "copy", "-movflags", "+faststart", str(output),
        ], cwd=source.parent, check=True, capture_output=True,
           text=True, timeout=900)
        return validate_render(output)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    finally:
        local_srt.unlink(missing_ok=True)
