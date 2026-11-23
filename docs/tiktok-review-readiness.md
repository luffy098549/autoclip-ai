# TikTok developer website readiness (not yet approved)

This branch contains a public marketing page at `/about` and **unfinished legal drafts** at `/terms` and `/privacy`. Do not submit these drafts to TikTok as final policies. They deliberately return `X-Robots-Tag: noindex`.

## Domain verification

If TikTok Developer Portal supplies a **plain-text verification file** for the website root, configure:

- `TIKTOK_VERIFICATION_FILENAME`: the exact `.txt` filename supplied by TikTok, without directories.
- `TIKTOK_VERIFICATION_CONTENT`: the exact one-line verification content supplied by TikTok.

Both are required; the endpoint is otherwise disabled (404). The endpoint never reads a file from disk. Copy the values from the developer portal, not from examples. If TikTok instead supplies a DNS verification record, configure DNS rather than this endpoint. Do not use this route for OAuth callbacks or tokens.

## Outstanding blockers before TikTok review

1. Confirm the operator's legal identity/contact, effective date, retention/deletion practices, processors and applicable jurisdiction. Replace legal drafts with accurate reviewed policies and remove the draft/noindex behavior only then.
2. Deploy the approved branch on a stable HTTPS hostname and verify `/about`, `/terms`, `/privacy` and (if requested) the exact verification file with HTTP 200 and valid TLS.
3. Implement the official TikTok OAuth login/redirect/callback using an exact registered HTTPS redirect URI, CSRF state validation, secure token storage, explicit scopes and revocation. Existing integration readiness flags **do not** constitute OAuth.
4. Verify permitted product/scopes and record a real demo of consent and upload/review workflow, with publishing disabled until user approval.
5. Run CI and real integration checks; a passing unit test does not prove TikTok review approval.

No TikTok client secret, access token, OAuth code, callback query, or private user information belongs in this document or logs.
