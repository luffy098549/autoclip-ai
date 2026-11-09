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
10. Until worker processing is enabled, run `docker compose exec web python -m scripts.process_clip CLIP_ID` (replace ID with the number shown).
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
