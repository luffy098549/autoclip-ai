"""Deterministic candidate selection scaffolding; not an AI prediction."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Candidate:
    start: float
    end: float
    score: float
    reason: str = ""


def _finite_number(value):
    """Reject booleans, nonnumeric inputs and integers too large for floats."""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def select_candidates(candidates: list[Candidate], *, threshold: float = 75.0,
                      max_count: int = 5, max_overlap_ratio: float = 0.25) -> list[Candidate]:
    """Select non-duplicated, valid candidate time ranges sorted by score."""
    if (type(max_count) is not int or not 1 <= max_count <= 5
            or not _finite_number(threshold) or not 0 <= threshold <= 100
            or not _finite_number(max_overlap_ratio)
            or not 0 <= max_overlap_ratio <= 1):
        raise ValueError("Invalid candidate selection settings")
    valid = [candidate for candidate in candidates
             if isinstance(candidate, Candidate)
             and all(_finite_number(v) for v in (candidate.start, candidate.end, candidate.score))]
    selected = []
    for candidate in sorted(valid, key=lambda x: (-x.score, x.start, x.end)):
        if candidate.start < 0 or candidate.end <= candidate.start:
            continue
        # Reject windows that cannot be represented as a positive millisecond
        # duration or whose subtraction overflows to infinity.
        duration = candidate.end - candidate.start
        # Bound clips to a day: enormous finite values otherwise become
        # unbounded millisecond integers and unusable FFmpeg clip requests.
        if not math.isfinite(duration) or not 0.001 <= duration <= 86400:
            continue
        # FFmpeg/subtitle boundaries are millisecond-based. A positive float
        # interval can still collapse after conversion to integer milliseconds.
        try:
            start_ms = int(candidate.start * 1000)
            end_ms = int(candidate.end * 1000)
        except (OverflowError, ValueError):
            continue
        if end_ms <= start_ms:
            continue
        if not 0 <= candidate.score <= 100 or candidate.score < threshold:
            continue
        overlap = False
        for existing in selected:
            existing_start_ms = int(existing.start * 1000)
            existing_end_ms = int(existing.end * 1000)
            # Identical millisecond windows are duplicates even when callers
            # permit 100% overlap between distinct windows.
            if start_ms == existing_start_ms and end_ms == existing_end_ms:
                overlap = True
                break
            shared = max(0, min(end_ms, existing_end_ms) - max(start_ms, existing_start_ms))
            shorter = min(end_ms - start_ms, existing_end_ms - existing_start_ms)
            if shorter <= 0 or shared / shorter > max_overlap_ratio:
                overlap = True
                break
        if not overlap:
            selected.append(candidate)
        if len(selected) >= max_count:
            break
    return selected
