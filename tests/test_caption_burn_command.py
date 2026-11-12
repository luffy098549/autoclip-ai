"""Ensure subtitle rendering cannot interact with stdin or overwrite clips."""
from unittest.mock import patch

from app.services.caption_burn import burn_subtitles


def test_caption_burn_disables_stdin_and_overwrite(tmp_path):
    source = tmp_path / "source.mp4"
    srt = tmp_path / "captions.srt"
    target = tmp_path / "captioned.mp4"
    source.write_bytes(b"synthetic")
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    with patch("app.services.caption_burn.subprocess.run") as run, \
         patch("app.services.caption_burn.validate_render", return_value={"duration": 1}):
        burn_subtitles(source, srt, target)
    command = run.call_args.args[0]
    assert "-nostdin" in command
    assert "-n" in command
    assert "-y" not in command
    assert not list(tmp_path.glob(".autoclip-sub-*.srt"))
