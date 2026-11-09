"""Transcript-derived candidate windows. Heuristic prototype, not viral prediction."""
import re
from ..services.candidates import Candidate, select_candidates

CUES = {
    "increíble", "increible", "espera", "mira", "brutal", "ganó", "gano",
    "no puede", "no me", "¿qué", "que pasó", "qué pasó", "wow", "omg",
    "what", "wait", "amazing", "bro", "impresionante", "no way", "nunca",
}


def score_candidates(transcript_segments: list[dict], *,
                     minimum_seconds: float = 18,
                     maximum_seconds: float = 65,
                     max_clips: int = 5) -> list[Candidate]:
    """Return nonoverlapping candidate windows from timed text; scoring is experimental."""
    if minimum_seconds <= 0 or maximum_seconds < minimum_seconds:
        raise ValueError("Invalid duration constraints")
    segments = sorted(
        (s for s in transcript_segments if float(s["end"]) > float(s["start"])),
        key=lambda x: float(x["start"]),
    )
    out = []
    for i, begin in enumerate(segments):
        start = float(begin["start"])
        covered = []
        for segment in segments[i:]:
            end = float(segment["end"])
            if end - start > maximum_seconds:
                break
            covered.append(segment)
            span = end - start
            if span < minimum_seconds:
                continue
            text = " ".join(str(s["text"]).strip() for s in covered).strip()
            words = re.findall(r"\b[\wáéíóúüñÁÉÍÓÚÜÑ]+\b", text, re.UNICODE)
            if len(words) < 20:
                continue
            lowered = text.casefold()
            cues = sum(1 for word in CUES if word in lowered)
            expressions = min(4, text.count("!") + text.count("?") + text.count("¡") + text.count("¿"))
            density = len(words) / max(span, 1.0)
            diversity = len(set(w.casefold() for w in words)) / len(words)
            score = min(100.0, 48 + min(cues, 4) * 6 + expressions * 3
                        + min(1.8, density) * 5 + diversity * 11)
            out.append(Candidate(start, end, round(score, 1),
                                 reason="Heuristic score from timed transcript"))
            # One candidate of roughly 30-55 seconds per starting segment.
            if span >= 35:
                break
    return select_candidates(out, threshold=65, max_count=max_clips)
