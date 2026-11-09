"""Official Instagram Graph API Reels publishing adapter.

Requires an Instagram Professional account, Meta app, authorized token and
a public HTTPS video URL hosted on an owner-controlled domain.
Never invoked by the automatic scheduler.
"""
from urllib.parse import urlsplit
import time


class InstagramPublishError(RuntimeError):
    pass


def validate_owned_video_url(video_url, permitted_host):
    parts = urlsplit(str(video_url))
    host = (parts.hostname or "").lower()
    allowed = str(permitted_host or "").lower().strip()
    if (parts.scheme != "https" or not allowed or host != allowed
            or parts.username or parts.password or not parts.path):
        raise ValueError("An HTTPS video on your configured media host is required")
    return video_url


def _post(session, url, token, data):
    response = session.post(
        url, data=data, headers={"Authorization": "Bearer " + token}, timeout=30
    )
    if response.status_code >= 400:
        raise InstagramPublishError("Meta API returned HTTP " + str(response.status_code))
    result = response.json()
    if result.get("error"):
        raise InstagramPublishError("Meta API rejected the publishing request")
    return result


def create_reel_container(
    video_url, caption, *, instagram_user_id, access_token,
    allowed_media_host, session, version="v25.0"
):
    validate_owned_video_url(video_url, allowed_media_host)
    if not str(instagram_user_id).isdigit() or not access_token:
        raise ValueError("Instagram Professional account and OAuth token required")
    result = _post(session,
        f"https://graph.facebook.com/{version}/{instagram_user_id}/media",
        access_token,
        {"media_type": "REELS", "video_url": video_url, "caption": str(caption)[:2200]}
    )
    container_id = result.get("id")
    if not container_id:
        raise InstagramPublishError("Meta API did not return a creation ID")
    return container_id


def reel_status(container_id, *, access_token, session, version="v25.0"):
    response = session.get(
        f"https://graph.facebook.com/{version}/{container_id}",
        params={"fields": "status_code"},
        headers={"Authorization": "Bearer " + access_token}, timeout=30
    )
    if response.status_code >= 400:
        raise InstagramPublishError("Meta container status HTTP " + str(response.status_code))
    return response.json().get("status_code", "UNKNOWN")


def publish_reel_container(
    container_id, *, instagram_user_id, access_token, session, version="v25.0"
):
    if not str(container_id).isdigit() or not str(instagram_user_id).isdigit():
        raise ValueError("A valid container and professional account are required")
    result = _post(session,
        f"https://graph.facebook.com/{version}/{instagram_user_id}/media_publish",
        access_token, {"creation_id": container_id}
    )
    if not result.get("id"):
        raise InstagramPublishError("Meta API did not confirm a media ID")
    return result["id"]


def upload_reel(
    video_url, caption, *, instagram_user_id, access_token,
    allowed_media_host, confirmed_by_owner=False, session=None, version="v25.0"
):
    if not confirmed_by_owner:
        raise PermissionError("Owner must explicitly approve the Reels publication")
    if session is None:
        try:
            import requests
        except ImportError as exc:
            raise InstagramPublishError("Install requirements-social.txt") from exc
        session = requests
    container = create_reel_container(
        video_url, caption, instagram_user_id=instagram_user_id,
        access_token=access_token, allowed_media_host=allowed_media_host,
        session=session, version=version
    )
    for _ in range(20):
        status = reel_status(container, access_token=access_token,
                             session=session, version=version)
        if status == "FINISHED":
            return publish_reel_container(
                container, instagram_user_id=instagram_user_id,
                access_token=access_token, session=session, version=version
            )
        if status in ("ERROR", "EXPIRED"):
            raise InstagramPublishError("Meta rejected or expired the Reels container")
        time.sleep(5)
    raise InstagramPublishError(
        "Container has not finished processing. Check its status before retrying."
    )
