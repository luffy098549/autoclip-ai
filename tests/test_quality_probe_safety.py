"""Regression checks for FFprobe validation in the render pipeline."""
import json
import subprocess
from unittest.mock import patch

import pytest

from app.quality import MediaValidationError, inspect_video


@pytest.mark.parametrize("width,height", [
    (True, 180), (320, False), ("320", 180),
    (320.5, 180), (None, 180), (320, -1),
])
def test_rejects_non_integer_or_invalid_dimensions(tmp_path, width, height):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"synthetic")
    payload = {"streams": [{"codec_type": "video", "width": width,
                            "height": height}],
               "format": {"duration": "12"}}
    with patch("app.quality.shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("app.quality.subprocess.run") as run:
        run.return_value.stdout = json.dumps(payload)
        with pytest.raises(MediaValidationError):
            inspect_video(source)


def test_probe_never_reads_interactive_stdin(tmp_path):
    source = tmp_path / "authorized.mp4"
    source.write_bytes(b"synthetic")
    payload = {"streams": [{"codec_type": "video", "width": 320,
                            "height": 180}, {"codec_type": "audio"}],
               "format": {"duration": "12"}}
    with patch("app.quality.shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("app.quality.subprocess.run") as run:
        run.return_value.stdout = json.dumps(payload)
        assert inspect_video(source)["duration"] == 12
        assert run.call_args.kwargs["stdin"] is subprocess.DEVNULL
