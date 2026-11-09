# AutoClip AI architecture (initial state)

## Principles

- **Own media or licensed sources first.** Content from third-party creators cannot be downloaded and reposted just because it is public.
- **Publishing disabled by default.** The interface must never imply that scheduled posts are actually being sent.
- **One accountable state record per clip and platform.** Use database transactions and unique idempotency keys before enabling real schedulers.
- **Separation of concerns.** Flask for read APIs and dashboard; workers for long-running editing; FFmpeg for deterministic exports; PostgreSQL for durable state.
- **No secrets in public repositories.** Only the empty/example environment file may be committed.
- **No reliance on competitor earnings estimates.** Analyze public engagement signals and privately authorized account metrics separately.

## Planned lifecycle

1. Register creator/source with verified permission.
2. Ingest file into private object storage; store checksum to avoid duplicates.
3. Extract source metadata and speech transcription.
4. Score highlight candidates and de-duplicate overlapping segments.
5. Edit video with original narrative/context and timed subtitles.
6. Validate audio, frame size, duration and editorial rights.
7. Reserve publishing slots with database locks.
8. Upload via official supported platform integration and approved account.
9. Reconcile remote status; log errors and retries.
10. Import metrics from owned accounts to drive experiments.

## Security requirements before launch

- Authenticated user sessions and CSRF protection on all writes
- OAuth with minimal necessary scopes, encrypted refresh tokens and rotation
- Role-gated account actions and audit logs
- Object storage access control and retention policies
- A legal rights review process and ability to take down clips
- API quotas, retries with idempotency and publish confirmation
- Production secret management, database migrations and monitoring

## What currently works

Dashboard page and read-only APIs, database schema initialization,
local licensed-video clip production, FFmpeg validation, SRT generation
helpers, deterministic candidate filtering and publication slot calculations.

Everything else remains development work.
