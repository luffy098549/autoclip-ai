"""Explicitly authorized source -> vertical clip; does not publish online."""
from pathlib import Path
from .quality import inspect_video, validate_render
from .video import render_vertical_clip


class RightsNotConfirmed(PermissionError):
    pass


def create_local_clip(source, destination, *, start, end, authorized=False):
    if not authorized:
        raise RightsNotConfirmed("Source must be authorized before editing")
    if end <= start or start < 0:
        raise ValueError("Invalid clip timestamps")
    source_info = inspect_video(source)
    if end > source_info["duration"] + 0.05:
        raise ValueError("Clip exceeds source duration")
    if not source_info["has_audio"]:
        raise ValueError("Source has no audio")
    out = Path(destination)
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite {out}")
    result = render_vertical_clip(source, out, start, end)
    try:
        return {"path": result, "source": source_info, "export": validate_render(result)}
    except Exception:
        out.unlink(missing_ok=True)
        raise
