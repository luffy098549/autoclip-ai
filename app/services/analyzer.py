"""Reusable analysis service called by a Celery worker or local CLI."""
from pathlib import Path
import math


def _validate_source_path(source_uri):
    """Accept only existing local video files, without leaking their paths."""
    if not isinstance(source_uri, str) or not source_uri.strip() or chr(0) in source_uri:
        raise ValueError("Invalid local source path")
    try:
        source = Path(source_uri)
        is_file = source.is_file()
    except (OSError, ValueError):
        raise ValueError("Invalid local source path") from None
    if not is_file:
        raise FileNotFoundError("Source video is missing")
    return source


def _validate_transcription(result):
    """Validate model output before persisting any transcript rows."""
    if not isinstance(result, dict):
        raise ValueError("Transcription must be a mapping")
    language = result.get("language")
    segments = result.get("segments")
    if not isinstance(language, str) or not language.strip() or len(language) > 20:
        raise ValueError("Invalid transcription language")
    if not isinstance(segments, (list, tuple)):
        raise ValueError("Transcription segments must be a sequence")
    cleaned = []
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError("Invalid transcription segment")
        start, end, text = (segment.get(key) for key in ("start", "end", "text"))
        if type(start) not in (int, float) or type(end) not in (int, float):
            raise ValueError("Invalid transcription timestamps")
        try:
            start, end = float(start), float(end)
        except (OverflowError, ValueError):
            raise ValueError("Invalid transcription timestamps") from None
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            raise ValueError("Invalid transcription timestamps")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Invalid transcription text")
        cleaned.append((float(start), float(end), text.strip()))
    return language.strip(), cleaned


from ..models import db, MediaSource, Clip, TranscriptSegment
from .rights import assess_rights
from .transcription import transcribe_file
from ..intelligence.highlights import score_candidates
from ..intelligence.audio_peaks import detect_audio_peaks


def analyze_source(source_id: int, *, model_size="small", max_clips=5):
    if type(source_id) is not int or source_id < 1:
        raise ValueError("source_id must be a positive integer")
    if type(max_clips) is not int or not 1 <= max_clips <= 5:
        raise ValueError("max_clips must be an integer between 1 and 5")
    source = db.session.get(MediaSource, source_id)
    if not source:
        raise ValueError("Source does not exist")
    if not assess_rights(source.rights_status, source.permission_evidence).allowed:
        raise PermissionError("Rights must be confirmed before transcription")
    _validate_source_path(source.source_uri)
    try:
        transcript = TranscriptSegment.query.filter_by(source_id=source.id).order_by(
            TranscriptSegment.start_seconds).all()
        if not transcript:
            result = transcribe_file(source.source_uri, model_size=model_size)
            language, segments = _validate_transcription(result)
            for start, end, text in segments:
                db.session.add(TranscriptSegment(
                    source_id=source.id, start_seconds=start, end_seconds=end,
                    text=text, language=language))
            db.session.flush()
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
    except Exception:
        db.session.rollback()
        raise
