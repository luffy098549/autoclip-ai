"""Speech-to-text adapter; install and configure faster-whisper in a later phase."""


class TranscriptionNotConfigured(RuntimeError):
    pass


def transcribe_file(path: str):
    raise TranscriptionNotConfigured(
        "Speech recognition isn't installed yet. No transcription was performed."
    )
