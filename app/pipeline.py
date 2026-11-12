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
    # Reject non-numeric and non-finite timestamps before touching media or disk.
    if (isinstance(start, bool) or isinstance(end, bool)
            or not isinstance(start, (int, float))
            or not isinstance(end, (int, float))
            or not math.isfinite(start) or not math.isfinite(end)
            or end <= start or start < 0):
        raise ValueError("Invalid clip timestamps")
    source_info = inspect_video(source)
    duration = source_info["duration"]
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid source duration")
    if end > duration + 0.05:
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
        # FFmpeg can leave an incomplete export even when rendering itself fails.
        out.unlink(missing_ok=True)
        raise
