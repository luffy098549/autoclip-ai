# Social platform integration status

## YouTube
Official YouTube Data API `videos.insert` is integrated into a **manual, owner-confirmed local CLI**, not a web scheduler. A Google OAuth desktop client and `youtube.upload` scope are required. Uploads must respect the actual rights to the original or licensed material. See `scripts/youtube_oauth.py` and `scripts/publish_youtube.py`.

## Instagram Reels
Two-stage Instagram Graph API helpers exist in `app/publishers/instagram.py`:

1. `create_reel_container` accepts a publicly accessible HTTPS video URL and creates a media container.
2. `get_reel_status` checks its readiness; `publish_reel` requires a separate explicit approval.

The account needs to be an Instagram Professional account with the appropriate content publishing permissions. A completed OAuth flow, a suitable media URL on a persistent host, and a compliant login setup remain prerequisites. No endpoint in the Flask dashboard activates this integration.

Reference: https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api

## TikTok
`create_inbox_draft` uses the official Content Posting API `video.upload` endpoint with `PULL_FROM_URL`; this creates a draft in the creator's inbox. The creator must finish and publish it in TikTok. Requires TikTok developer registration, app approval, authorized user token, and a verified public video-hosting domain.

`check_inbox_status` checks the remote upload request. Direct Post needs separate `video.publish` approval, creator-info checks and platform-specific consent, and is **not** implemented here.

References: https://developers.tiktok.com/docs/en/content-posting-api-get-started-upload-content and https://developers.tiktok.com/docs/en/content-posting-api-get-started

## Why cloud publishing is off

Render deployment is read-only because the workspace currently has a billing suspension and this project has no durable, secure shared object storage. OAuth tokens must be kept out of GitHub; the project does not have a secure vault/token rotation service yet. Do not enable automatic publication or direct public posting until those controls and compliance checks exist.

These helpers were tested with stubbed HTTP responses, not live social accounts.
