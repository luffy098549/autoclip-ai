"""Safe SRT formatting and timestamp helpers."""
from datetime import timedelta


def srt_timestamp(seconds: float) -> str:
    if seconds < 0:
        raise ValueError("Timestamp cannot be negative")
    millis = round(seconds * 1000)
    hours, remainder = divmod(millis, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    whole_seconds, ms = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{ms:03}"


def build_srt(segments: list[dict]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        start = float(segment["start"])
        end = float(segment["end"])
        if end <= start:
            raise ValueError("Subtitle end must follow its start")
        text = str(segment["text"]).strip().replace("\r", " ")
        if not text:
            continue
        blocks.append(f"{index}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")
