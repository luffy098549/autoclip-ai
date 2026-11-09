# AutoClip AI

A Python-based starter platform for producing **authorized, original** short-form video content.

## Implemented
- Flask HTTP health and status endpoints
- PostgreSQL/SQLAlchemy source, creator, clip and publication data models
- Redis/Celery worker and beat scaffolding
- Deterministic 120-minute minimum separation and 5-publication daily maximum per platform
- Local FFmpeg 1080x1920 render from an authorized input video
- ffprobe source inspection + output quality validation
- Command-line preview workflow and unit tests
- Docker Compose for local development

## Not yet implemented
Automated Kick/YouTube downloads, AI highlight selection, speech-to-text,
automatic subtitles, official YouTube/TikTok/Instagram OAuth and uploads,
analytics, production scheduling with transactional database locks, rights
verification beyond explicit user attestation, and a complete dashboard.
**No social media uploads happen in this version.**

## Setup
1. Install Docker and Docker Compose, or Python 3.12+ and FFmpeg.
2. Copy `.env.example` to `.env`; set your own secret and DB password. Do not commit `.env`.
3. Run `docker compose up --build -d`.
4. Run `docker compose exec web python -m scripts.init_db`.
5. Open `http://localhost:8000/health` and `http://localhost:8000/api/status`.

### Local video proof of concept
For development outside Docker, install dependencies from `requirements.txt`
and ensure `ffmpeg` and `ffprobe` are available on PATH.

```bash
python -m scripts.clip_local input.mp4 output.mp4 --start 10 --end 35 --authorized
python -m pytest -q
```

The `--authorized` flag is your explicit confirmation that you have the rights to
edit the supplied video. It is not a legal verification mechanism. Do not
upload or repost footage unless permission and platform eligibility are established.

## Publishing configuration
Initial targets: YouTube Shorts, TikTok and Instagram Reels.
- Minimum separation per platform: **120 minutes**
- Maximum per platform per New York calendar day: **5**
- Example daily slots: 10:00, 12:00, 14:00, 16:00, 18:00 America/New_York
- Actual publishing remains disabled until official integrations are implemented.

## Security
Never commit API keys, OAuth tokens, user credentials, personal media or
private recordings. The repo is public. All social account authentication
must use official OAuth and secrets must remain server-side.

## Development roadmap
1. Local media pipeline and robust validation
2. Authorized media import and persistent jobs
3. Whisper transcription and highlight scoring
4. Automatic subtitles, audio processing and editable templates
5. Platform authorization, rate limits, publication and verification
6. Analytics, experiments, alerts and production deployment
