# Render demonstration deployment

This repository includes a Render Blueprint at `render.yaml`, configured for a **read-only demonstration**. It does not enable live clipping, source uploads or social publishing.

## Deploy the web demo

1. Sign in to https://dashboard.render.com/ and select New -> Blueprint.
2. Connect GitHub and select `luffy098549/autoclip-ai`.
3. Inspect `render.yaml` and current pricing before approving resource creation.
4. Render will provision the Flask web service and PostgreSQL 16 database, build the Docker image and apply Alembic migrations at startup.
5. Set a secret `ADMIN_PASSWORD_HASH` in the Render dashboard only if you want private dashboard access. Generate it with `python -m scripts.hash_password` locally, **never commit it**.
6. Open the URL assigned by Render and verify `/health` and the homepage.

## Why this is a read-only demo

The web service has an ephemeral local filesystem. Production media rendering needs shared, durable object storage (such as S3-compatible storage) accessible to both the web service and Celery worker, plus secure authenticated downloads. The demo intentionally sets `READ_ONLY_DEPLOYMENT=true` and disables processing and publishing.

The free tier may sleep, be rate-limited, or have database expiration rules. It is intended for trying the UI, not running a channel business. For production, provision persistent storage, cloud worker, HTTPS, OAuth, rate limiting and a suitable paid database.

Before switching off the read-only flag, implement persistent media storage, worker availability and a full security review. Do **not** disable it just to make upload buttons work.

## Database URL

Render supplies `postgresql://` to `DATABASE_URL`; the Flask factory normalizes it to `postgresql+psycopg://` for the psycopg 3 driver already in requirements.
