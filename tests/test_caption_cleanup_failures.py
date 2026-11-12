"""Cleanup errors must not conceal the original FFmpeg failure."""
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.caption_burn import burn_subtitles


@pytest.mark.parametrize("blocked", ["output", "temporary", "both"])
def test_cleanup_permission_errors_preserve_ffmpeg_failure(tmp_path, blocked):
    source = tmp_path / "source.mp4"
    subtitles = tmp_path / "source.srt"
    output = tmp_path / "captioned.mp4"
    source.write_bytes(b"synthetic source")
    subtitles.write_text("synthetic subtitle", encoding="utf-8")

    def failed_ffmpeg(*_args, **_kwargs):
        output.write_bytes(b"partial render")
        raise RuntimeError("original ffmpeg error")

    original_unlink = Path.unlink

    def guarded_unlink(path, *args, **kwargs):
        is_temp = path.name.startswith(".autoclip-sub-")
        if (path == output and blocked in ("output", "both")) or (
            is_temp and blocked in ("temporary", "both")
        ):
            raise PermissionError("synthetic cleanup failure")
        return original_unlink(path, *args, **kwargs)

    with patch("app.services.caption_burn.subprocess.run", side_effect=failed_ffmpeg), \
         patch("pathlib.Path.unlink", autospec=True, side_effect=guarded_unlink):
        with pytest.raises(RuntimeError, match="original ffmpeg error"):
            burn_subtitles(source, subtitles, output)

    assert output.exists() == (blocked in ("output", "both"))
    assert len(list(tmp_path.glob(".autoclip-sub-*.srt"))) == int(
        blocked in ("temporary", "both")
    )
