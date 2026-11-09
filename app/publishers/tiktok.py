"""TikTok Content Posting API Direct Post - owner-initiated, FILE_UPLOAD.

Requires approved video.publish scope, account-level consent, and a fresh
account token. The returned publish_id is a processing job, not proof of posting.
"""
from pathlib import Path
from urllib.parse import urlsplit

INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
CREATOR_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"


class TikTokPublishError(RuntimeError):
    pass


def chunk_plan(video_size, chunk_size=10_000_000):
    if not isinstance(video_size, int) or video_size <= 0 or video_size > 4_000_000_000:
        raise ValueError("TikTok video size must be 1 byte to 4 GB")
    if video_size < 5_000_000:
        return video_size, 1
    size = min(chunk_size, video_size)
    if size < 5_000_000 or size > 64_000_000:
        raise ValueError("Chunk size must be between 5 and 64 MB")
    count = max(1, video_size // size)
    if count > 1000:
        raise ValueError("Too many video chunks")
    return size, count


def _post(session, url, token, payload):
    response = session.post(
        url, json=payload,
        headers={"Authorization": "Bearer " + token}, timeout=30
    )
    if response.status_code >= 400:
        raise TikTokPublishError("TikTok returned HTTP " + str(response.status_code))
    result = response.json()
    error = result.get("error", {})
    if error.get("code") != "ok":
        raise TikTokPublishError(
            "TikTok refused request: " + str(error.get("code") or "unknown")
        )
    return result.get("data") or {}


def creator_options(token, session):
    info = _post(session, CREATOR_URL, token, {})
    return info.get("privacy_level_options") or []


def upload_video(
    path, caption, *, access_token, approved_by_owner=False,
    privacy_level="SELF_ONLY", is_ai_generated=False,
    branded_content=False, organic_business_content=False, session=None
):
    if not approved_by_owner:
        raise PermissionError("Creator must explicitly authorize the post and its settings")
    if not access_token:
        raise ValueError("An account-authorized TikTok access token is required")
    video = Path(path)
    if not video.is_file() or video.suffix.lower() != ".mp4":
        raise ValueError("A local MP4 file is required")
    if len(str(caption)) > 2200:
        raise ValueError("TikTok caption is too long")
    if session is None:
        try:
            import requests
        except ImportError as exc:
            raise TikTokPublishError("Install requirements-social.txt") from exc
        session = requests

    options = creator_options(access_token, session)
    if privacy_level not in options:
        raise TikTokPublishError("Privacy setting is not allowed for this creator")
    size = video.stat().st_size
    chunk_size, count = chunk_plan(size)
    data = _post(session, INIT_URL, access_token, {
        "post_info": {
            "title": str(caption),
            "privacy_level": privacy_level,
            "disable_duet": False, "disable_comment": False,
            "disable_stitch": False,
            "brand_content_toggle": bool(branded_content),
            "brand_organic_toggle": bool(organic_business_content),
            "is_aigc": bool(is_ai_generated),
        },
        "source_info": {
            "source": "FILE_UPLOAD", "video_size": size,
            "chunk_size": chunk_size, "total_chunk_count": count,
        }
    })
    upload_url = str(data.get("upload_url") or "")
    parts = urlsplit(upload_url)
    if parts.scheme != "https" or not (parts.hostname or "").endswith(".tiktokapis.com"):
        raise TikTokPublishError("TikTok returned an invalid upload URL")
    if parts.username or parts.password:
        raise TikTokPublishError("Unexpected credentials in upload URL")
    publish_id = data.get("publish_id")
    if not publish_id:
        raise TikTokPublishError("TikTok did not provide a publish identifier")

    # All chunks sequentially; last chunk includes remaining bytes.
    start = 0
    with video.open("rb") as stream:
        for n in range(count):
            length = size - start if n == count - 1 else chunk_size
            chunk = stream.read(length)
            if len(chunk) != length:
                raise TikTokPublishError("Video changed while being read")
            response = session.put(
                upload_url, data=chunk,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(length),
                    "Content-Range": f"bytes {start}-{start+length-1}/{size}",
                },
                timeout=180,
            )
            expected = 201 if n == count - 1 else 206
            if response.status_code != expected:
                # Never include upload_url, whose query contains short-lived tokens.
                raise TikTokPublishError("Chunk transfer returned HTTP " +
                                         str(response.status_code))
            start += length
    return str(publish_id)
