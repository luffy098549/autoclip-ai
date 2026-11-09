"""Public-channel descriptive comparisons, not revenue inference."""
from statistics import median


def relative_performance(views: int, comparable_views: list[int]) -> float:
    """Views / median of a comparable channel sample; not a virality prediction."""
    if not comparable_views:
        return 0.0
    base = median(max(0, n) for n in comparable_views)
    return round(views / base, 2) if base > 0 else 0.0
