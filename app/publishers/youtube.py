"""YouTube uploader planned. Official OAuth credentials and API review required."""
from .base import PublishingDisabled


def upload_short(*_args, **_kwargs):
    raise PublishingDisabled("YouTube OAuth and videos.insert integration not configured")
