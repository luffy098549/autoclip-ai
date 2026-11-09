"""Authorized synthetic video -> transcript -> multiple vertical clips and SRT.

Whisper is stubbed to keep CI deterministic; actual FFmpeg rendering is real.
No third-party content, downloads, OAuth or publishing.
"""
import shutil
import subprocess
from unittest.mock import patch

import pytest
from flask_migrate import upgrade

from app import create_app
from app.models import db, MediaSource, Clip
from app.services.analyzer import analyze_source
from app.services.clip_processor import process_clip
from app.quality import inspect_video


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and ffprobe required",
)
def test_authorized_video_generates_multiple_reviewable_clips(tmp_path):
    source_file = tmp_path / "owned-synthetic.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=10",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=22050",
        "-t", "43", "-c:v", "mpeg4", "-q:v", "9",
        "-c:a", "aac", "-shortest", str(source_file),
    ], check=True, timeout=90)

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "pipeline.sqlite"),
        "SECRET_KEY": "test-only",
        "MEDIA_ROOT": str(tmp_path / "media"),
        "AUTO_CAPTION_ENABLED": False,
    })
    words = "wow this is an amazing original synthetic moment with lots of interesting details " * 3
    transcript = {
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 20.0, "text": words},
            {"start": 21.0, "end": 41.0, "text": words},
        ],
    }
    with app.app_context():
        upgrade()
        source = MediaSource(
            source_uri=str(source_file), rights_status="owned",
            permission_evidence="Synthetic media generated in this test",
        )
        db.session.add(source)
        db.session.commit()
        with patch("app.services.analyzer.transcribe_file", return_value=transcript) as whisper:
            result = analyze_source(source.id, max_clips=5)
        whisper.assert_called_once()
        assert len(result["clip_ids"]) >= 2
        for clip_id in result["clip_ids"][:2]:
            rendered = process_clip(clip_id)
            video = inspect_video(rendered["path"])
            assert (video["width"], video["height"]) == (1080, 1920)
            assert video["has_audio"]
            clip = db.session.get(Clip, clip_id)
            assert clip.editorial_status == "ready"
            assert (tmp_path / "media" / "subtitles" / f"clip-{clip_id}.srt").is_file()
        assert not list((tmp_path / "media").rglob("*published*"))
