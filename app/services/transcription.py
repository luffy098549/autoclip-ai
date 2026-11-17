"""Optional local speech-to-text via faster-whisper. No cloud upload."""
import os
import math
from pathlib import Path


class TranscriptionNotConfigured(RuntimeError):
    pass


def transcribe_file(path: str, *, model_size: str | None = None,
                    device: str | None = None, compute_type: str = "int8") -> dict:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionNotConfigured(
            "Install optional dependency: pip install -r requirements-ai.txt"
        ) from exc
    model = WhisperModel(model_size or os.getenv("WHISPER_MODEL", "small"),
                         device=device or os.getenv("WHISPER_DEVICE", "cpu"),
                         compute_type=compute_type)
    segments, info = model.transcribe(str(source), vad_filter=True, beam_size=5)
    cleaned = []
    for seg in segments:
        # Reject malformed and sub-millisecond cues before storing metadata.
        try:
            start, end = float(seg.start), float(seg.end)
        except (TypeError, ValueError, OverflowError):
            continue
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
            continue
        # Very large finite seconds may overflow when converted to milliseconds.
        scaled_start, scaled_end = start * 1000, end * 1000
        if not (math.isfinite(scaled_start) and math.isfinite(scaled_end)):
            continue
        start_ms, end_ms = round(scaled_start), round(scaled_end)
        if end_ms <= start_ms:
            continue
        text = str(seg.text).replace("\x00", "").strip()
        if text:
            cleaned.append({"start": start_ms / 1000,
                            "end": end_ms / 1000, "text": text})
    return {"language":info.language or "unknown", "segments":cleaned}
