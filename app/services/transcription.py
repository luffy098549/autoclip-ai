"""Optional local speech-to-text via faster-whisper. No cloud upload."""
import os
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
        text = seg.text.strip()
        if text and seg.end > seg.start:
            cleaned.append({"start":round(float(seg.start), 3),
                            "end":round(float(seg.end), 3), "text":text})
    return {"language":info.language or "unknown", "segments":cleaned}
