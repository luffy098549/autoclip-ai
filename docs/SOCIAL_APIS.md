# Official social platform integrations — current limits

Each platform requires the owner to authorize a developer app and approve each posting action. AutoClip AI never requests account passwords or stores OAuth tokens in GitHub.

## YouTube

An OAuth2 manual uploader is available. Run the local authorization and explicit command described in YOUTUBE_UPLOAD.md. The upload uses the official videos.insert endpoint and is private by default.

## TikTok

The adapter in app/publishers/tiktok.py follows Content Posting API Direct Post:
- Requires your app to have approved video.publish scope and your own authorized account token.
- Queries creator_info first and checks permitted privacy settings.
- Calls video/init and uploads sequential chunks to the returned TikTok upload URL.
- Returns a publish_id **job identifier**, not a confirmed public post. Final status needs reconciliation through the Post Status API.
- Unaudited apps can only post privately, and developer review is needed before public posts.

An upload requires explicit per-post consent and confirmation of AI-generated / branded content where applicable. OAuth token acquisition and TikTok app review remain user-side prerequisites. No public posting via automation is enabled.

## Instagram

The Graph API adapter in app/publishers/instagram.py:
- Requires a Professional Instagram account authorized for content publishing.
- Requires an owner-controlled, publicly accessible HTTPS media URL on an approved host (e.g. object storage CDN).
- Creates a REELS media container, polls for processing completion, and publishes only after an explicit per-post confirmation.
- Returns a media ID. This is real publication, not a draft — caller must obtain the owner's explicit confirmation.

Instagram OAuth, professional account enrollment and durable object storage are still prerequisites. The web dashboard does not expose social tokens and does not schedule direct publishing.

## Operational safeguards

- Keep provider tokens in a private secret manager, outside the repository and web browser.
- Do not automatically repost livestreams or copyrighted creator footage without permissions.
- Respect user consent, community rules and platform rate limits.
- Reconcile uncertain upload outcomes before retrying to avoid duplicate posts.
- The website remains a local editorial/preview system until official permissions, secure storage and end-to-end integration are tested with real accounts.

Official references:
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post
- https://developers.tiktok.com/docs/en/content-posting-api-media-transfer-guide
- https://developers.facebook.com/docs/instagram-platform/content-publishing/
