"""Transcript-derived candidate windows. Heuristic prototype, not viral prediction."""
import re
import math
from ..services.candidates import Candidate, select_candidates

CUES = {
    "increíble", "increible", "espera", "mira", "brutal", "ganó", "gano",
    "no puede", "no me", "¿qué", "que pasó", "qué pasó", "wow", "omg",
    "what", "wait", "amazing", "bro", "impresionante", "no way", "nunca",
}


def _finite_number(value):
    """Accept only finite real numeric values, excluding booleans and huge integers."""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, ValueError, TypeError):
        return False


def _valid_audio_peaks(peaks):
    """Discard malformed optional peaks rather than aborting transcript analysis."""
    if not isinstance(peaks, (list, tuple)):
        return []
    # A provider may emit the same audio frame more than once. Count each
    # timestamp only once so duplicates cannot inflate highlight rankings.
    strongest_by_time = {}
    for peak in peaks:
        if not isinstance(peak, (list, tuple)) or len(peak) != 2:
            continue
        timestamp, strength = peak
        if _finite_number(timestamp) and _finite_number(strength) and timestamp >= 0:
            strongest_by_time[timestamp] = max(
                strongest_by_time.get(timestamp, 0.0), strength
            )
    return sorted(strongest_by_time.items())


def score_candidates(transcript_segments: list[dict], *,
                     minimum_seconds: float = 18,
                     maximum_seconds: float = 65,
                     max_clips: int = 5,
                     audio_peaks: list[tuple[float, float]] | None = None) -> list[Candidate]:
    """Return nonoverlapping candidate windows from timed text; scoring is experimental."""
    if (any(type(x) not in (int, float) for x in (minimum_seconds, maximum_seconds))
            or not all(_finite_number(x) for x in (minimum_seconds, maximum_seconds))
            or minimum_seconds <= 0 or maximum_seconds < minimum_seconds
            or type(max_clips) is not int or not 1 <= max_clips <= 5):
        raise ValueError("Invalid duration constraints")
    audio_peaks = _valid_audio_peaks(audio_peaks)
    # A missing or malformed provider transcript is not a sequence of segments.
    # In particular, dictionaries and strings should not be iterated as entries.
    if not isinstance(transcript_segments, (list, tuple)):
        return []
    segments = []
    for segment in transcript_segments:
        # Transcription providers may return malformed entries; ignore them
        # rather than aborting the whole analysis job.
        if not isinstance(segment, dict):
            continue
        try:
            start, end = float(segment["start"]), float(segment["end"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
            continue
        segments.append({"start": start, "end": end, "text": str(segment.get("text") or "")})
    segments.sort(key=lambda x: x["start"])
    out = []
    for i, begin in enumerate(segments):
        start = float(begin["start"])
        covered = []
        furthest_end = start
        for segment in segments[i:]:
            # Nested Whisper segments can end earlier than a preceding segment.
            # Use the furthest covered timestamp for both continuity and bounds.
            if covered and float(segment["start"]) - furthest_end > 4:
                break
            next_end = max(furthest_end, float(segment["end"]))
            if next_end - start > maximum_seconds:
                break
            furthest_end = next_end
            end = furthest_end
            covered.append(segment)
            span = end - start
            if span < minimum_seconds:
                continue
            text = " ".join(str(s["text"]).strip() for s in covered).strip()
            words = re.findall(r"\b[\wáéíóúüñÁÉÍÓÚÜÑ]+\b", text, re.UNICODE)
            if len(words) < 20:
                continue
            lowered = text.casefold()
            cues = sum(1 for cue in CUES if re.search(
                r"(?<!\w)" + re.escape(cue) + r"(?!\w)", lowered
            ))
            expressions = min(4, text.count("!") + text.count("?") + text.count("¡") + text.count("¿"))
            density = len(words) / max(span, 1.0)
            diversity = len(set(w.casefold() for w in words)) / len(words)
            audio_bonus = 0.0
            if audio_peaks:
                audio_bonus = min(12.0, sum(
                    min(1.0, max(0.0, strength)) * 4.0
                    for timestamp, strength in audio_peaks
                    if start <= timestamp < end
                ))
            score = min(100.0, 48 + min(cues, 4) * 6 + expressions * 3
                        + min(1.8, density) * 5 + diversity * 11 + audio_bonus)
            out.append(Candidate(start, end, round(score, 1),
                                 reason="Heuristic score from timed transcript"))
            # One candidate of roughly 30-55 seconds per starting segment.
            if span >= 35:
                break
    return select_candidates(out, threshold=65, max_count=max_clips)
