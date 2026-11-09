import pytest
from app.publishers.youtube import upload_short, VALID_PRIVACY
from app.publishers.base import PublishingDisabled


def test_missing_video_is_rejected_before_api_call(tmp_path):
    with pytest.raises(ValueError):
        upload_short(tmp_path/"missing.mp4", "Demo")


def test_title_and_privacy_validation_before_social_dependencies(tmp_path):
    media=tmp_path/"clip.mp4"
    media.write_bytes(b"test")
    with pytest.raises(ValueError):
        upload_short(media, " ")
    with pytest.raises(ValueError):
        upload_short(media, "Test", privacy_status="invalid")
    with pytest.raises(ValueError):
        upload_short(media, "Test", made_for_kids="no")
    assert VALID_PRIVACY == {"private", "public", "unlisted"}


def test_missing_optional_library_can_be_handled(tmp_path):
    media=tmp_path/"clip.mp4"
    media.write_bytes(b"test")
    try:
        upload_short(media, "Original recording", token_path=tmp_path/"missing-token.json")
    except PublishingDisabled:
        pass
    except Exception as exc:
        # An installed Google client with missing local OAuth credentials also fails safe.
        assert "token" in str(exc).lower() or "requirements-social" in str(exc)
