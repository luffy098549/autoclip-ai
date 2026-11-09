"""Official Instagram Reels container lifecycle.

Requires a Professional Instagram account, OAuth authorization, and a publicly
reachable HTTPS video URL. No scheduled uploads are enabled.
"""
import ipaddress
import re
from urllib.parse import urlsplit
from .base import PublishingDisabled


def validate_public_media_url(url):
    parts = urlsplit(str(url))
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host or parts.username or parts.password:
        raise ValueError("Video must use a public HTTPS URL")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Private video hosts are not allowed")
    try:
        ipaddress.ip_address(host)
        raise ValueError("Use a verified public domain, not an IP address")
    except ValueError as exc:
        if "not an IP address" in str(exc):
            raise
    if "." not in host:
        raise ValueError("A public hostname is required")
    if parts.fragment:
        raise ValueError("Video URL must not include a fragment")
    return str(url)


def _endpoint(identifier, action="", version="v25.0"):
    if not str(identifier).isdigit() or not re.fullmatch(r"v\d+\.\d+", version):
        raise ValueError("Invalid Instagram identifier or API version")
    return f"https://graph.facebook.com/{version}/{identifier}" + (f"/{action}" if action else "")


def _session(session):
    if session is not None:
        return session
    try:
        import requests
    except ImportError as exc:
        raise PublishingDisabled("Install requirements-social.txt") from exc
    return requests


def create_reel_container(ig_user_id, video_url, caption, access_token, *,
                          approved=False, session=None, version="v25.0"):
    """Start an upload container; does not publish the reel."""
    if not approved:
        raise PublishingDisabled("Explicit owner approval required")
    if not access_token:
        raise PublishingDisabled("Instagram OAuth token required")
    url = validate_public_media_url(video_url)
    response = _session(session).post(
        _endpoint(ig_user_id, "media", version), timeout=30,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"media_type":"REELS","video_url":url,
              "caption":str(caption)[:2200],"share_to_feed":"false"},
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("id"):
        raise RuntimeError("Instagram did not return a media container ID")
    return str(data["id"])


def get_reel_status(container_id, access_token, *, session=None, version="v25.0"):
    if not access_token:
        raise PublishingDisabled("Instagram OAuth token required")
    response = _session(session).get(
        _endpoint(container_id, version=version), timeout=30,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": "status_code"},
    )
    response.raise_for_status()
    return response.json().get("status_code", "UNKNOWN")


def publish_reel(ig_user_id, container_id, access_token, *,
                 approved=False, session=None, version="v25.0"):
    """Publish only with fresh explicit approval and a FINISHED media container."""
    if not approved:
        raise PublishingDisabled("Explicit owner approval required for publishing")
    if not access_token:
        raise PublishingDisabled("Instagram OAuth token required")
    if get_reel_status(container_id, access_token, session=session,
                       version=version) != "FINISHED":
        raise RuntimeError("Reel container is not ready to publish")
    response = _session(session).post(
        _endpoint(ig_user_id, "media_publish", version), timeout=30,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"creation_id": str(container_id)},
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("id"):
        raise RuntimeError("Instagram did not confirm a media ID")
    return str(data["id"])


def upload_reel(*args, **kwargs):
    """Prevent accidental old-call automatic uploads; use two-stage approval."""
    raise PublishingDisabled("Use create_reel_container and publish_reel with approval")
