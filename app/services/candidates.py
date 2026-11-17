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
        if not 0 <= candidate.score <= 100 or candidate.score < threshold:
            continue
        overlap = False
        for existing in selected:
            shared = max(0.0, min(candidate.end, existing.end) - max(candidate.start, existing.start))
            shorter = min(candidate.end - candidate.start, existing.end - existing.start)
            if shared / shorter > max_overlap_ratio:
                overlap = True
                break
        if not overlap:
            selected.append(candidate)
        if len(selected) >= max_count:
            break
    return selected
