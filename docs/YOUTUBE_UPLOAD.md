# YouTube upload — manual, account-authorized first step

YouTube uses OAuth 2.0 for videos.insert; a public API key is not sufficient for uploading. AutoClip AI uses the least privilege scope youtube.upload. Neither OAuth tokens nor the app client secret belongs in GitHub.

## Prerequisites

- A YouTube channel that you own or are authorized to operate.
- A Google Cloud project with YouTube Data API v3 enabled.
- An OAuth client configured for a desktop app, plus the required OAuth consent configuration. Google may restrict unverified projects.
- A locally running AutoClip AI database with a completed, reviewed MP4 in storage/clips.
- Rights to publish source material. Having access to a public livestream does not in itself grant reuse rights.

## Step-by-step

1. Install optional dependencies: pip install -r requirements-social.txt
2. Place OAuth client JSON at storage/private/youtube-client.json (never in the repo).
3. Run python -m scripts.youtube_oauth and approve access to your own channel.
4. Review your clip and choose an audience declaration (made for kids: yes/no).
5. Upload manually, starting with private visibility:

    python -m scripts.publish_youtube 3 --title "Mi clip original" --privacy private --made-for-kids no --confirm-reviewed-and-authorized

Replace clip ID 3 with the actual database ID. Add --description and --token if needed. The code calls the official resumable videos.insert API and stores the YouTube video ID in the publications table.

For public uploads the owner must explicitly set --privacy public. Never assume monetization approval or that clips of other creators meet reused-content requirements.

## Duplicate prevention

The uploader serializes writes per platform in PostgreSQL, checks two-hour spacing and the daily five-video limit, and reserves a publication record before any network upload. If a network failure makes upload status uncertain, the record moves to needs_review and blocks retries for that clip. Inspect YouTube Studio to reconcile it manually.

**This is not an automatic publisher.** The scheduling UI still contains drafts, and no worker autonomously calls this uploader. TikTok and Instagram need their own platform authorizations and app review.
