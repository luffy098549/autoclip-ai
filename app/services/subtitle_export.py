"""Export original Whisper transcript segments to a sidecar .srt file."""
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
    sub = [row for row in sub if row["end"] > row["start"]]
    if not sub:
        return None
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects previously reviewed sidecars from retries.
    # If the write fails, remove only the file created by this attempt.
    with dest.open("x", encoding="utf-8") as handle:
        try:
            handle.write(build_srt(sub))
        except BaseException:
            handle.close()
            dest.unlink(missing_ok=True)
            raise
    return dest
