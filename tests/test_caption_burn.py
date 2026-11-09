import pytest
from app.services.caption_burn import burn_subtitles


def test_missing_video(tmp_path):
    srt=tmp_path / "sub.srt"
    srt.write_text("example",encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        burn_subtitles(tmp_path / "missing.mp4",srt,tmp_path / "output.mp4")


def test_refuse_in_place_overwrite(tmp_path):
    video=tmp_path / "video.mp4"
    subtitles=tmp_path / "captions.srt"
    video.write_bytes(b"placeholder")
    subtitles.write_text("sample",encoding="utf-8")
    with pytest.raises(ValueError):
        burn_subtitles(video,subtitles,video)
