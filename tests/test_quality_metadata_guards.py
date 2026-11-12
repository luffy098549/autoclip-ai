"""Reject malformed ffprobe metadata before accepting a render."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.quality import MediaValidationError, inspect_video, validate_render


@pytest.mark.parametrize("duration", ["NaN", "Infinity", "-Infinity", "0", "-1"])
def test_inspect_rejects_nonfinite_or_nonpositive_duration(tmp_path, duration):
    video = tmp_path / "source.mp4"
    video.touch()
    payload = {"streams": [{"codec_type": "video", "width": 640, "height": 360}],
               "format": {"duration": duration}}
    with patch("app.quality.shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("app.quality.subprocess.run", return_value=SimpleNamespace(stdout=json.dumps(payload))):
        with pytest.raises(MediaValidationError):
            inspect_video(video)


@pytest.mark.parametrize("width,height", [(0, 1080), (1920, 0), (-1, 1080)])
def test_inspect_rejects_invalid_dimensions(tmp_path, width, height):
    video = tmp_path / "source.mp4"
    video.touch()
    payload = {"streams": [{"codec_type": "video", "width": width, "height": height}],
               "format": {"duration": "30.0"}}
    with patch("app.quality.shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("app.quality.subprocess.run", return_value=SimpleNamespace(stdout=json.dumps(payload))):
        with pytest.raises(MediaValidationError):
            inspect_video(video)


@pytest.mark.parametrize("minimum", [float("nan"), float("inf"), -1, 0])
def test_validate_render_rejects_invalid_minimum_without_probing(minimum):
    with patch("app.quality.inspect_video") as inspect:
        with pytest.raises(MediaValidationError):
            validate_render("anything.mp4", expected_min_seconds=minimum)
        inspect.assert_not_called()
