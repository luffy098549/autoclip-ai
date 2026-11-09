# Development guide

## Local setup

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Generate a secret for `SECRET_KEY` with `python -c "import secrets;print(secrets.token_hex(32))"`.
4. Generate a password hash using `python -m scripts.hash_password` from an environment with project dependencies installed; copy its result to `ADMIN_PASSWORD_HASH` in your private `.env`.
5. Run `docker compose up --build -d`.
6. Run `docker compose exec web python -m scripts.init_db`.
7. Open `http://localhost:8000/login` and sign in.
8. Register a channel in Streamers, then upload a **licensed or owned** video in Clips.
9. In Clips, create a recut request with start and end seconds.
10. With Docker, PROCESSING_ENABLED=true sends work to the Celery worker automatically. If it is disabled or unavailable, run `docker compose exec web python -m scripts.process_clip CLIP_ID` (replace ID with the number shown).
11. Inspect rendered clips in `storage/clips/`. Online publishing is deliberately disabled.

## Before using any public internet hosting

The current dashboard is a development MVP, not a hardened multiuser production service. Put it behind HTTPS, set SESSION_COOKIE_SECURE=true, use proper secret management, add login rate limiting and server-side session management, and deploy production database migrations. Never deploy this as-is with a development password or predictable SECRET_KEY.

## Developer checks

```bash
python -m compileall -q app scripts run.py tests
python -m pytest -q
```

Video validation uses ffprobe. Automatic render uses FFmpeg. Source permissions must be documented and confirmed by the owner. Flags and text fields are attestations, **not** independent legal verification.

Publishing remains OFF; official API connections, original-content editorial checks, and OAuth are future stages.

## Optional Whisper AI processing

To build the optional AI image:

1. Set `INSTALL_AI=true` in your shell environment before calling Docker Compose, or add it to the local `.env`.
2. Set `AI_ENABLED=true` in your local `.env` (not in GitHub).
3. Rebuild: `docker compose build --no-cache` and `docker compose up -d`.
4. Initialize new tables: `docker compose exec web python -m scripts.init_db`.
5. Run `docker compose exec web python -m scripts.analyze_source SOURCE_ID --render`.
6. Inspect the created clips and sidecar SRT subtitles in your `storage/` directory.

Automatic selection uses a preliminary timing-and-language heuristic based on Whisper.
It does not guarantee viral clips, contextual accuracy or platform monetization.
The published video must still be editorially reviewed.

### Limitations

- `AI_ENABLED` enables a Celery task endpoint but does not grant Kick, YouTube, TikTok or Instagram permissions.
- `PROCESSING_ENABLED` only queues FFmpeg work; it **does not** enable social media uploads.
- The repository has no production-ready database migration mechanism yet. The initial `create_all` is a development aid.
