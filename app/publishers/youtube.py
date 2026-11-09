"""Explicit, owner-initiated YouTube Data API uploads. Nothing runs on a timer."""
import os
from pathlib import Path

from .base import PublishingDisabled

SCOPES = ("https://www.googleapis.com/auth/youtube.upload",)
VALID_PRIVACY = {"private", "unlisted", "public"}


def load_authorized_credentials(token_path):
    """Refresh OAuth2 credentials without asking for a password."""
    path = Path(token_path).expanduser()
    if not path.is_file():
        raise PublishingDisabled("YouTube OAuth token absent; run scripts.youtube_oauth first")
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError as exc:
        raise PublishingDisabled(
            "Install requirements-social.txt for official YouTube uploads"
        ) from exc
    credentials = Credentials.from_authorized_user_file(str(path), SCOPES)
    if credentials.valid:
        return credentials
    if not (credentials.expired and credentials.refresh_token):
        raise PublishingDisabled("YouTube OAuth token must be renewed by the account owner")
    credentials.refresh(Request())
    # OAuth credential files are private and never committed to a public repository.
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    handle = os.open(path, flags, 0o600)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write(credentials.to_json())
    finally:
        path.chmod(0o600)
    return credentials


def upload_short(
    video_path,
    title,
    description="",
    *,
    token_path="storage/private/youtube-token.json",
    privacy_status="private",
    made_for_kids=None,
    client=None,
):
    """Upload an explicitly reviewed MP4; return the remote video ID.

    An OAuth-authorized googleapiclient client may be injected in unit tests.
    """
    video = Path(video_path)
    if not video.is_file() or video.suffix.lower() != ".mp4":
        raise ValueError("A local MP4 file is required")
    title = str(title).strip()
    if not title or len(title) > 100:
        raise ValueError("YouTube title must contain 1 to 100 characters")
    if len(str(description)) > 5000:
        raise ValueError("YouTube description is too long")
    if privacy_status not in VALID_PRIVACY:
        raise ValueError("privacy_status must be private, unlisted, or public")
    if made_for_kids is not None and not isinstance(made_for_kids, bool):
        raise ValueError("made_for_kids must be true/false or omitted")
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise PublishingDisabled(
            "Install requirements-social.txt to enable YouTube upload"
        ) from exc
    if client is None:
        client = build(
            "youtube", "v3", credentials=load_authorized_credentials(token_path),
            cache_discovery=False
        )

    status = {"privacyStatus": privacy_status}
    if made_for_kids is not None:
        status["selfDeclaredMadeForKids"] = made_for_kids
    media = MediaFileUpload(str(video), mimetype="video/mp4",
                            chunksize=8 * 1024 * 1024, resumable=True)
    request = client.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title, "description": str(description),
                "categoryId": "22",
            },
            "status": status,
        },
        media_body=media,
    )
    result = None
    while result is None:
        _, result = request.next_chunk(num_retries=2)
    if not result or not result.get("id"):
        raise RuntimeError("YouTube did not return a video ID; check account history")
    return str(result["id"])
