"""Rank existing authorized clip candidates into a daily *manual review* queue.

This module never downloads media or publishes to social platforms.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite


@dataclass(frozen=True)
class RankedClip:
    clip_id: int
    source_id: int
    start_seconds: float
    end_seconds: float
    score: float


def select_daily_clips(clips, *, target=5, max_per_source=3, overlap_tolerance=0.1):
    """Select up to target diverse clips, favoring quality over a forced quota.

    Accepts Clip ORM instances or equivalent objects. The caller must restrict
    candidates to authorized sources and an appropriate editorial status.
    """
    if target < 1 or max_per_source < 1:
        raise ValueError("target and max_per_source must be positive")
    candidates = []
    for clip in clips:
        score = clip.score
        start, end = float(clip.start_seconds), float(clip.end_seconds)
        if score is None or not all(isfinite(v) for v in (float(score), start, end)):
            continue
        if end <= start or float(score) < 65:
            continue
        candidates.append(RankedClip(clip.id, clip.source_id, start, end, float(score)))
    candidates.sort(key=lambda c: (-c.score, c.source_id, c.start_seconds, c.clip_id))
    selected = []
    counts = {}
    seen_ids = set()
    for clip in candidates:
        if clip.clip_id in seen_ids or counts.get(clip.source_id, 0) >= max_per_source:
            continue
        if any(
            clip.source_id == prior.source_id
            and min(clip.end_seconds, prior.end_seconds)
                - max(clip.start_seconds, prior.start_seconds) > overlap_tolerance
            for prior in selected
        ):
            continue
        selected.append(clip)
        seen_ids.add(clip.clip_id)
        counts[clip.source_id] = counts.get(clip.source_id, 0) + 1
        if len(selected) == target:
            break
    return selected
