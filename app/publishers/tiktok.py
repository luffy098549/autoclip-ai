"""TikTok Content Posting API integration placeholder."""
from .base import PublishingDisabled


def upload_video(*_args, **_kwargs):
    raise PublishingDisabled("TikTok approved video.publish integration not configured")
