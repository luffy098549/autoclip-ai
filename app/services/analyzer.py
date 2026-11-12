"""Reusable analysis service called by a Celery worker or local CLI."""
from pathlib import Path
from ..models import db, MediaSource, Clip, TranscriptSegment
from .rights import assess_rights
from .transcription import transcribe_file
from ..intelligence.highlights import score_candidates
from ..intelligence.audio_peaks import detect_audio_peaks


def analyze_source(source_id: int, *, model_size="small", max_clips=5):
    if not 1 <= max_clips <= 5:
        raise ValueError("max_clips must be between 1 and 5")
    source = db.session.get(MediaSource, source_id)
    if not source:
        raise ValueError("Source does not exist")
    if not assess_rights(source.rights_status, source.permission_evidence).allowed:
        raise PermissionError("Rights must be confirmed before transcription")
    if not Path(source.source_uri).is_file():
        raise FileNotFoundError("Source video is missing")
    transcript = TranscriptSegment.query.filter_by(source_id=source.id).order_by(
        TranscriptSegment.start_seconds).all()
    if not transcript:
        result = transcribe_file(source.source_uri, model_size=model_size)
        for s in result["segments"]:
            db.session.add(TranscriptSegment(
                source_id=source.id, start_seconds=s["start"], end_seconds=s["end"],
                text=s["text"], language=result["language"]))
        db.session.commit()
        transcript = TranscriptSegment.query.filter_by(source_id=source.id).order_by(
            TranscriptSegment.start_seconds).all()
    try:
        audio_peaks = detect_audio_peaks(source.source_uri)
    except (OSError, RuntimeError, ValueError):
        audio_peaks = []  # Transcript-only scoring remains available.
    candidates = score_candidates([
        {"start": t.start_seconds, "end": t.end_seconds, "text": t.text}
        for t in transcript
    ], max_clips=max_clips, audio_peaks=audio_peaks)
    ids = []
    for choice in candidates:
        existing = Clip.query.filter_by(
            source_id=source.id, start_seconds=choice.start, end_seconds=choice.end).first()
        if existing:
            ids.append(existing.id)
        else:
            clip = Clip(source_id=source.id, start_seconds=choice.start,
                        end_seconds=choice.end, score=choice.score,
                        editorial_status="awaiting_worker")
            db.session.add(clip)
            db.session.flush()
            ids.append(clip.id)
    db.session.commit()
    return {"source_id": source_id, "clip_ids": ids,
            "transcript_segments": len(transcript), "audio_peaks": len(audio_peaks),
            "candidate_count": len(ids)}
