"""TikTok Content Posting API: owner-approved upload to TikTok inbox.

This sends a DRAFT for user completion in the TikTok app. It does not
silently publish to TikTok or circumvent platform approval/review.
"""
from .base import PublishingDisabled
from .instagram import validate_public_media_url

INIT_ENDPOINT="https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
STATUS_ENDPOINT="https://open.tiktokapis.com/v2/post/publish/status/fetch/"


def _session(session):
    if session is not None:
        return session
    try:
        import requests
    except ImportError as exc:
        raise PublishingDisabled("Install requirements-social.txt") from exc
    return requests


def create_inbox_draft(video_url, access_token, *,
                       approved=False, session=None):
    if not approved:
        raise PublishingDisabled("Owner approval required before sending to TikTok")
    if not access_token:
        raise PublishingDisabled("Authorized TikTok video.upload token required")
    url=validate_public_media_url(video_url)
    response=_session(session).post(
        INIT_ENDPOINT, timeout=30,
        headers={"Authorization":f"Bearer {access_token}",
                 "Content-Type":"application/json"},
        json={"source_info":{"source":"PULL_FROM_URL","video_url":url}},
    )
    response.raise_for_status()
    data=response.json()
    err=data.get("error") or {}
    if err.get("code") != "ok" or not (data.get("data") or {}).get("publish_id"):
        raise RuntimeError("TikTok did not accept the inbox draft request")
    return str(data["data"]["publish_id"])


def check_inbox_status(publish_id, access_token, *, session=None):
    if not access_token:
        raise PublishingDisabled("Authorized TikTok token required")
    if not publish_id or len(str(publish_id)) > 64:
        raise ValueError("Invalid TikTok publish ID")
    response=_session(session).post(
        STATUS_ENDPOINT, timeout=30,
        headers={"Authorization":f"Bearer {access_token}",
                 "Content-Type":"application/json"},
        json={"publish_id":str(publish_id)},
    )
    response.raise_for_status()
    result=response.json()
    if (result.get("error") or {}).get("code") != "ok":
        raise RuntimeError("TikTok status request failed")
    return result.get("data", {})


def upload_video(*args, **kwargs):
    raise PublishingDisabled(
        "Use create_inbox_draft and finish the post in the TikTok app"
    )
