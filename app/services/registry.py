"""Supported providers and launch-state capabilities."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    name: str
    can_monitor_metadata: bool
    can_download_media: bool
    can_publish: bool


PROVIDERS = {
    "kick": Provider("Kick", False, False, False),
    "youtube": Provider("YouTube", False, False, False),
    "tiktok": Provider("TikTok", False, False, False),
    "instagram": Provider("Instagram", False, False, False),
}
