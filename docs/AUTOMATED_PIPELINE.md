# End-to-end AI video clipping (local, authorized media)

AutoClip AI can run a local pipeline from an imported source file to multiple finished 9:16 videos. It never ingests a public stream or publishes a clip to a social network automatically.

## Requirements
- Python 3.12+, FFmpeg built with subtitle/libass support.
- Install optional `requirements-ai.txt` including faster-whisper.
- PostgreSQL initialized with Alembic migrations.
- Video imported using the owner-only dashboard, with documented rights evidence.
- For subtitle burn-in, make sure the FFmpeg subtitles filter is installed.

## One-command example

```bash
python -m scripts.pipeline_full 1 --model small --max-clips 5 --burn-subtitles
```

The command will load the authorized video, transcribe speech locally with faster-whisper, store timed segments, identify up to five high-scoring non-overlapping candidates, render vertical MP4 videos with FFmpeg, create sidecar SRT files and optionally burn subtitles into finished MP4s.

All clips require **human editorial review**. Ranking is a language-cue heuristic: not a validated virality predictor or guarantee of monetization. It does not automatically add substantive original commentary, detect faces or guarantee context. Weak source content can result in zero clips.

If using the dashboard with Celery, set `AI_ENABLED=true`, `AUTO_RENDER_ENABLED=true`, and `AUTO_CAPTION_ENABLED=true` after verifying the optional dependencies and storage. Do not activate these in the read-only Render demo.

## Security and privacy

Transcripts are only accessible through the authenticated /api/sources/SOURCE_ID/transcript endpoint. The frontend displays them with textContent to prevent injection. Media remains in private local storage and must not be committed to GitHub.
