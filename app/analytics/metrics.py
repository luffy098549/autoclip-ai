"""Compare supplied performance snapshots; no fabricated channel revenue."""


def engagement_percent(views: int, likes: int, comments: int, shares: int) -> float:
    """Simple engagement proxy; platform-specific definitions can differ."""
    if views <= 0:
        return 0.0
    return round(100 * (likes + comments + shares) / views, 2)
