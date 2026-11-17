"""Safe SRT formatting and timestamp helpers."""
import math


def srt_timestamp(seconds: float) -> str:
    """Convert a finite, nonnegative number of seconds to an SRT timestamp."""
    if isinstance(seconds, bool):
        raise ValueError("Timestamp must be a finite nonnegative number")
    try:
        value = float(seconds)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Timestamp must be a finite nonnegative number") from None
    if not math.isfinite(value) or value < 0:
        raise ValueError("Timestamp must be a finite nonnegative number")
    scaled = value * 1000
    if not math.isfinite(scaled):
        raise ValueError("Timestamp exceeds supported range")
    millis = round(scaled)
    hours, remainder = divmod(millis, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    whole_seconds, ms = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{ms:03}"


def build_srt(segments: list[dict]) -> str:
    """Produce sequentially numbered cues, rejecting invalid timing and unsafe text."""
    blocks = []
    for segment in segments:
        start_stamp = srt_timestamp(segment["start"])
        end_stamp = srt_timestamp(segment["end"])
        start = float(segment["start"])
        end = float(segment["end"])
        if end <= start:
            raise ValueError("Subtitle end must follow its start")
        text = str(segment["text"]).strip().replace("\r", " ").replace("\x00", "")
        if not text:
            continue
        blocks.append(f"{len(blocks) + 1}\n{start_stamp} --> {end_stamp}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")
