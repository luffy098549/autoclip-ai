"""Export original Whisper transcript segments to a sidecar .srt file."""
import os
import tempfile
from pathlib import Path
from ..models import db, Clip, TranscriptSegment
from .subtitles import build_srt


def export_clip_srt(clip_id: int, output_path: str | Path) -> Path | None:
    clip = db.session.get(Clip, clip_id)
    if clip is None:
        raise ValueError("Clip not found")
    rows = TranscriptSegment.query.filter(
        TranscriptSegment.source_id == clip.source_id,
        TranscriptSegment.end_seconds > clip.start_seconds,
        TranscriptSegment.start_seconds < clip.end_seconds,
    ).order_by(TranscriptSegment.start_seconds).all()
    if not rows:
        return None
    duration = clip.end_seconds - clip.start_seconds
    sub = [{"start": max(0, row.start_seconds - clip.start_seconds),
            "end": min(duration, row.end_seconds - clip.start_seconds),
            "text": row.text} for row in rows]
    sub = [row for row in sub if row["end"] > row["start"] and str(row["text"] or "").replace(chr(0), "").strip()]
    # SRT stores millisecond timestamps. Skip cues that round to the same
    # millisecond rather than aborting export of other valid speech.
    sub = [row for row in sub if round(row["start"] * 1000) != round(row["end"] * 1000)]
    if not sub:
        return None
    # Whitespace-only transcript segments produce no SRT cues. Do not create
    # an empty sidecar or request FFmpeg to burn unusable subtitles.
    content = build_srt(sub)
    if not content:
        return None
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # A failed write must not leave a truncated SRT for render workers.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=dest.parent,
            prefix=".autoclip-srt-", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, dest)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return dest
