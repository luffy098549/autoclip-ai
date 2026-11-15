"""Backfill preliminary scores for already-rendered clips.

Audio intensity is only a ranking proxy, not a virality prediction.
Existing scores are preserved. No uploads or re-renders.
"""
from pathlib import Path
from statistics import mean
from ..models import db, Clip, MediaSource, TranscriptSegment
from ..services.rights import assess_rights
from ..intelligence.audio_peaks import detect_audio_peaks
from ..intelligence.highlights import CUES


def score_existing_clips(*, limit=100):
    clips = (Clip.query.filter(Clip.editorial_status == "ready", Clip.score.is_(None))
             .order_by(Clip.id.asc()).limit(limit).all())
    sources = {s.id: s for s in MediaSource.query.filter(
        MediaSource.id.in_({c.source_id for c in clips})).all()} if clips else {}
    updated, skipped, errors = [], [], []
    audio_cache = {}
    for clip in clips:
        source = sources.get(clip.source_id)
        if not source or not assess_rights(source.rights_status, source.permission_evidence).allowed:
            skipped.append(clip.id)
            continue
        if not clip.output_path or not Path(clip.output_path).is_file():
            skipped.append(clip.id)
            continue
        duration = clip.end_seconds - clip.start_seconds
        if duration <= 0:
            skipped.append(clip.id)
            continue
        try:
            segments = (TranscriptSegment.query.filter_by(source_id=clip.source_id)
                        .filter(TranscriptSegment.end_seconds > clip.start_seconds,
                                TranscriptSegment.start_seconds < clip.end_seconds).all())
            text = " ".join(s.text for s in segments).casefold()
            if source.id not in audio_cache:
                audio_cache[source.id] = detect_audio_peaks(source.source_uri)
            peaks = [strength for at, strength in audio_cache[source.id]
                     if clip.start_seconds <= at < clip.end_seconds]
            # Baseline 65 allows existing manually edited clips into the review
            # queue; rank primarily by transcript signals and audio dynamics.
            # This is an *experimental proxy*, not an AI virality probability.
            cue_hits = sum(1 for cue in CUES if cue in text)
            speech_bonus = min(8, len(text.split()) / max(duration, 1) * 3)
            audio_bonus = min(12, len(peaks) * 1.5 + (mean(peaks) * 3 if peaks else 0))
            score = min(95, 65 + min(cue_hits, 4) * 3 + speech_bonus
                        + audio_bonus + min(3, text.count("!") + text.count("?")))
            clip.score = round(score, 1)
            updated.append({"clip_id": clip.id, "score": clip.score,
                            "method": "experimental_transcript_audio_heuristic"})
        except (OSError, ValueError, RuntimeError) as exc:
            errors.append({"clip_id": clip.id, "error": type(exc).__name__})
    db.session.commit()
    return {"updated": updated, "skipped": skipped, "errors": errors,
            "note": "Preliminary heuristic scores; not predicted views or virality"}
