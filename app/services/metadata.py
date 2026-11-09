"""Create editorial metadata; no fabricated quotes or misleading claims."""
import re


def sanitize_title(title: str, max_length: int = 95) -> str:
    compact = re.sub(r"\s+", " ", title).strip()
    if not compact:
        raise ValueError("Title must contain text")
    return compact[:max_length].rstrip()


def attribution(creator: str, source_url: str, commentary: str = "") -> str:
    """Attribution is not a substitute for permission to reuse source media."""
    return f"Fuente: {creator}\nOriginal: {source_url}\n{commentary}".strip()
