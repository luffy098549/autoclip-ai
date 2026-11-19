"""Explicitly authorized source -> vertical clip; does not publish online."""
import math
from pathlib import Path

from .quality import inspect_video, validate_render
from .media_probe import validate_clip_range
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
    if out.resolve() == Path(source).resolve():
        raise ValueError("Source and export destination must differ")
    if out.exists() or out.is_symlink():
        raise FileExistsError(f"Refusing to overwrite {out}")
    source_info = inspect_video(source)
    validated = validate_clip_range(
        {"duration_seconds": source_info["duration"]}, start, end,
    )
    if not source_info["has_audio"]:
        raise ValueError("Source has no audio")
    # render_vertical_clip owns and cleans its exclusive temporary file. Never
    # unlink the destination on failure: another worker may have won publication.
    result = render_vertical_clip(source, out, validated["start_seconds"], validated["end_seconds"])
    return {"path": result, "source": source_info, "export": validate_render(result)}


def create_local_clip_batch(source, output_dir, ranges, *, authorized=False):
    """Export up to five distinct authorized ranges; never publish to social networks.

    Each clip has a deterministic destination within output_dir. A failure leaves
    previously successful clips available for manual review, and never overwrites
    an existing export.
    """
    if not authorized:
        raise RightsNotConfirmed("Source must be authorized before editing")
    if not isinstance(ranges, (list, tuple)) or not 1 <= len(ranges) <= 5:
        raise ValueError("Provide between one and five clip ranges")
    source_info = inspect_video(source)
    if not source_info["has_audio"]:
        raise ValueError("Source has no audio")
    validated = []
    seen = set()
    for item in ranges:
        if not isinstance(item, dict) or set(item) != {"start", "end"}:
            raise ValueError("Each range needs start and end")
        segment = validate_clip_range(
            {"duration_seconds": source_info["duration"]}, item["start"], item["end"]
        )
        key = (segment["start_seconds"], segment["end_seconds"])
        if key in seen:
            raise ValueError("Duplicate clip range")
        seen.add(key)
        validated.append(segment)
    folder = Path(output_dir)
    targets = [folder / f"clip-{index:02d}.mp4"
               for index in range(1, len(validated) + 1)]
    # Preflight all paths before starting any encode. A source named clip-02.mp4
    # inside output_dir must not become the second destination after clip 01
    # has already been rendered. Resolve also catches alternate path spellings.
    source_path = Path(source).resolve()
    if any(target.resolve() == source_path for target in targets):
        raise ValueError("Source and export destination must differ")
    if any(target.exists() or target.is_symlink() for target in targets):
        raise FileExistsError("An export destination already exists")
    exports = []
    for target, segment in zip(targets, validated):
        result = render_vertical_clip(
            source, target, segment["start_seconds"], segment["end_seconds"]
        )
        exports.append({"path": result, "range": segment, "export": validate_render(result)})
    return {"source": source_info, "clips": exports}
