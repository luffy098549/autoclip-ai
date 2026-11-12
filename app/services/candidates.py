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
    if (not isinstance(max_count, int) or isinstance(max_count, bool)
            or max_count < 1
            or isinstance(threshold, bool) or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold) or not 0 <= threshold <= 100
            or isinstance(max_overlap_ratio, bool)
            or not isinstance(max_overlap_ratio, (int, float))
            or not math.isfinite(max_overlap_ratio)
            or not 0 <= max_overlap_ratio <= 1):
        raise ValueError("Invalid candidate selection settings")
    # Filter invalid scores before sorting: NaN does not have a stable
    # ordering and can displace legitimate high-scoring clips.
    valid = [
        candidate for candidate in candidates
        if all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v)
               for v in (candidate.start, candidate.end, candidate.score))
    ]
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
