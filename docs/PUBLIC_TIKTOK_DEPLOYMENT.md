# Public web deployment gate (TikTok integration)

The public pages in this branch are **drafts**, not final legal documents. Do not submit them to TikTok or mark the integration production-ready.

## Security before exposing Flask

Set these in the hosting provider's secret configuration (never commit values):

- `PUBLIC_DEPLOYMENT=true`: fails startup if production session requirements are not met.
- `SECRET_KEY`: stable, unpredictable secret with at least 32 characters; do not rotate per process or redeploy.
- `SESSION_COOKIE_SECURE=true`: send session cookies only over HTTPS.
- `READ_ONLY_DEPLOYMENT=true`: disables writes to `/api/` for a read-only demonstration. This is **not** a full authorization boundary; do not expose the administrative dashboard until authentication and rate limits are reviewed.
- `DATABASE_URL`: use a properly secured, provisioned database for application functionality. Never use development credentials in production.
- `ADMIN_PASSWORD_HASH`: leave unset for a public legal-page-only preview. Set only after authentication has been audited.

Do not publish a public service merely because `/health` returns 200. A health response is not proof that migrations, OAuth, privacy compliance or external permissions work.

## Legal pages

- `/about` — public product description
- `/terms` — **draft** terms, blocked from indexing
- `/privacy` — **draft** privacy policy, blocked from indexing

Before publishing final policies, provide the true operator identity and contact, effective date, jurisdiction, data collection and retention details, subprocessors, user rights and deletion request procedure. Remove draft warnings and noindex headers only after actual review. Never invent legal or contact details.

## TikTok

Copy the exact verification filename and token from the TikTok developer console into `TIKTOK_VERIFICATION_FILENAME` and `TIKTOK_VERIFICATION_CONTENT` (hosting configuration, not Git). The exact root-level `.txt` path is then served without filesystem access. This is only domain verification, **not OAuth**.

Register the exact HTTPS redirect URI supported by the implemented OAuth callback; validate `state`, token exchange and error handling with a test account and the permissions actually requested. Do not submit a fabricated demo video or claim app review is complete before external verification.

## Verification before approval

Run `python -m pytest -q tests/test_public_site.py tests/test_public_deployment_security.py` and full CI; check actual public HTTPS status and content for all three pages and the exact verification file. Confirm callback behavior without printing codes or tokens. Record the verified URLs and review status before notifying the user that the setup is ready.
