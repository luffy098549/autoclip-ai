"""Deterministic candidate selection scaffolding; not an AI prediction."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Candidate:
    start: float
    end: float
    score: float
    reason: str = ""


def select_candidates(candidates: list[Candidate], *, threshold: float = 75.0,
                      max_count: int = 5, max_overlap_ratio: float = 0.25) -> list[Candidate]:
    """Select non-duplicated, valid candidate time ranges sorted by score."""
    if (type(max_count) is not int or not 1 <= max_count <= 5
            or isinstance(threshold, bool) or not isinstance(threshold, (int, float))
            or isinstance(max_overlap_ratio, bool) or not isinstance(max_overlap_ratio, (int, float))
            or not math.isfinite(threshold) or not 0 <= threshold <= 100
            or not math.isfinite(max_overlap_ratio)
            or not 0 <= max_overlap_ratio <= 1):
        raise ValueError("Invalid candidate selection settings")
    valid = []
    for candidate in candidates:
        if not isinstance(candidate, Candidate):
            continue
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in (candidate.start, candidate.end, candidate.score)):
            continue
        valid.append(candidate)
    selected = []
    for candidate in sorted(valid, key=lambda x: (-x.score, x.start)):
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
