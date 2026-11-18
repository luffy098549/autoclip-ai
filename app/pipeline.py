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
    # Reject NaN, infinity, booleans and malformed values before invoking FFprobe.
    if (
        isinstance(start, bool) or isinstance(end, bool)
        or not isinstance(start, (int, float))
        or not isinstance(end, (int, float))
        or not math.isfinite(start) or not math.isfinite(end)
        or start < 0 or end <= start
    ):
        raise ValueError("Invalid clip timestamps")
    out = Path(destination)
    if out.exists() or out.is_symlink():
        raise FileExistsError(f"Refusing to overwrite {out}")
    source_info = inspect_video(source)
    if end > source_info["duration"] + 0.05:
        raise ValueError("Clip exceeds source duration")
    if not source_info["has_audio"]:
        raise ValueError("Source has no audio")
    # render_vertical_clip owns and cleans its exclusive temporary file. Never
    # unlink the destination on failure: another worker may have won publication.
    result = render_vertical_clip(source, out, start, end)
    return {"path": result, "source": source_info, "export": validate_render(result)}
