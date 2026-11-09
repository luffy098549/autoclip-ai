# AutoClip AI

Starter MVP for an authorized, original-content short-video production pipeline.

## Features available now
- Flask health endpoint and dashboard status API
- PostgreSQL schema via SQLAlchemy
- Redis/Celery queue scaffolding
- Local authorized video input with FFmpeg 9:16 rendering
- Per-platform scheduling: at least 120 minutes apart, maximum 5 posts daily
- Publishing integrations disabled until official APIs and authorization are configured

**Not yet implemented:** Kick/YouTube media ingestion, AI highlight selection, automated subtitles, direct social uploads, analytics, OAuth, or comprehensive rights verification.

## Quick start
1. Copy `.env.example` to `.env` and replace placeholder secrets.
2. Run `docker compose up --build`.
3. Visit `http://localhost:8000/health` or `/api/status`.
4. Run tests with `python -m pytest` in the configured environment.

Configured candidate slots: 10:00, 12:00, 14:00, 16:00, 18:00 America/New_York.

This is an early technical scaffold, not a production-ready autonomous publisher.
