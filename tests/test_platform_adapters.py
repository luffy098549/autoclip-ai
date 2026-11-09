import pytest
from app.publishers.base import PublishingDisabled
from app.publishers.instagram import validate_public_media_url, upload_reel
from app.publishers.tiktok import upload_video


def test_social_links_require_a_real_public_https_host():
    assert validate_public_media_url("https://media.example.com/my-clip.mp4").startswith("https://")
    for url in ("http://media.example.com/my-clip.mp4", "https://localhost/video.mp4",
                "https://127.0.0.1/clip.mp4", "file:///tmp/video.mp4"):
        with pytest.raises(ValueError):
            validate_public_media_url(url)


def test_legacy_unconfirmed_auto_publish_entrypoints_stay_disabled():
    # Only explicit, per-account steps in test_social_publisher_adapters.py
    # are allowed until OAuth and consent verification are complete.
    with pytest.raises(PublishingDisabled):
        upload_reel("any.mp4")
    with pytest.raises(PublishingDisabled):
        upload_video("any.mp4")
