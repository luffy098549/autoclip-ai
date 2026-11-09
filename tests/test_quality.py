import pytest
from app.quality import MediaValidationError, inspect_video


def test_nonexistent_video():
    with pytest.raises(MediaValidationError):
        inspect_video("/no-such-autoclip-video-file.mp4")
