"""Explicitly authorized source -> vertical clip; does not publish online."""
import math
from pathlib import Path
from .quality import inspect_video, validate_render
from .video import render_vertical_clip


class RightsNotConfirmed(PermissionError):
    pass


def create_local_clip(source, destination, *, start, end, authorized=False):
    if not authorized:
        raise RightsNotConfirmed("Source must be authorized before editing")
    try:
        start, end = float(start), float(end)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Invalid clip timestamps") from exc
    if not all(math.isfinite(v) for v in (start, end)) or end <= start or start < 0:
        raise ValueError("Invalid clip timestamps")
    source_info = inspect_video(source)
    if end > source_info["duration"] + 0.05:
        raise ValueError("Clip exceeds source duration")
    if not source_info["has_audio"]:
        raise ValueError("Source has no audio")
    out = Path(destination)
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite {out}")
    try:
        result = render_vertical_clip(source, out, start, end)
        return {"path": result, "source": source_info, "export": validate_render(result)}
    except Exception:
        # FFmpeg may leave a truncated MP4 when encoding fails. The output was
        # confirmed absent before rendering, so discard this attempt's artifact.
        out.unlink(missing_ok=True)
        raise
