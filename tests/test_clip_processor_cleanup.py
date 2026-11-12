"""Worker failures must not leave stale clips or erase existing exports."""
from pathlib import Path
from unittest.mock import patch

import pytest
from flask_migrate import upgrade

from app import create_app
from app.models import db, Clip, MediaSource
from app.services.clip_processor import process_clip


@pytest.fixture
def worker_case(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "worker.sqlite"),
        "SECRET_KEY": "test-only",
        "MEDIA_ROOT": str(tmp_path / "media"),
    })
    with app.app_context():
        upgrade()
        source = MediaSource(
            source_uri=str(tmp_path / "owned.mp4"),
            rights_status="owned",
            permission_evidence="Synthetic video created by this test",
        )
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=20,
                    score=90, editorial_status="awaiting_worker")
        db.session.add(clip)
        db.session.commit()
        yield app, clip.id, tmp_path / "media"


def test_subtitle_failure_removes_new_render_and_marks_failed(worker_case):
    app, clip_id, root = worker_case
    target = root / "clips" / f"clip-{clip_id}.mp4"

    def render(_source, destination, **_kwargs):
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        Path(destination).write_bytes(b"synthetic test export")
        return {"path": str(destination)}

    with app.app_context():
        with patch("app.services.clip_processor.create_local_clip", side_effect=render):
            with patch("app.services.subtitle_export.export_clip_srt",
                       side_effect=RuntimeError("subtitle writer failed")):
                with pytest.raises(RuntimeError, match="subtitle writer failed"):
                    process_clip(clip_id)
        assert not target.exists()
        assert db.session.get(Clip, clip_id).editorial_status == "failed"


def test_existing_export_survives_failed_worker_attempt(worker_case):
    app, clip_id, root = worker_case
    target = root / "clips" / f"clip-{clip_id}.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"previous export")
    with app.app_context():
        with patch("app.services.clip_processor.create_local_clip",
                   side_effect=FileExistsError("already exists")):
            with pytest.raises(FileExistsError):
                process_clip(clip_id)
        assert target.read_bytes() == b"previous export"
        assert db.session.get(Clip, clip_id).editorial_status == "failed"


def test_partial_render_is_removed_when_renderer_raises(worker_case):
    app, clip_id, root = worker_case
    target = root / "clips" / f"clip-{clip_id}.mp4"

    def failing_render(_source, destination, **_kwargs):
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        Path(destination).write_bytes(b"partial ffmpeg output")
        raise RuntimeError("ffmpeg failed")

    with app.app_context():
        with patch("app.services.clip_processor.create_local_clip",
                   side_effect=failing_render):
            with pytest.raises(RuntimeError, match="ffmpeg failed"):
                process_clip(clip_id)
        assert not target.exists()
        assert db.session.get(Clip, clip_id).editorial_status == "failed"


@pytest.mark.parametrize("preexisting", [False, True])
def test_caption_render_failure_preserves_existing_or_cleans_partial(worker_case, preexisting):
    app, clip_id, root = worker_case
    target = root / "clips" / f"clip-{clip_id}.mp4"
    captioned = root / "clips" / f"clip-{clip_id}-captioned.mp4"
    if preexisting:
        captioned.parent.mkdir(parents=True, exist_ok=True)
        captioned.write_bytes(b"previous captioned export")

    def render(_source, destination, **_kwargs):
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        Path(destination).write_bytes(b"new synthetic export")
        return {"path": str(destination)}

    def burn(_source, _subtitles, destination):
        Path(destination).write_bytes(b"partial captioned export")
        raise RuntimeError("caption ffmpeg failed")

    with app.app_context():
        app.config["AUTO_CAPTION_ENABLED"] = True
        with patch("app.services.clip_processor.create_local_clip", side_effect=render), \
             patch("app.services.subtitle_export.export_clip_srt", return_value=str(root / "subtitles" / "synthetic.srt")), \
             patch("app.services.caption_burn.burn_subtitles", side_effect=burn) as burn_mock:
            if preexisting:
                with pytest.raises(FileExistsError, match="Captioned export already exists"):
                    process_clip(clip_id)
                burn_mock.assert_not_called()
            else:
                with pytest.raises(RuntimeError, match="caption ffmpeg failed"):
                    process_clip(clip_id)
                burn_mock.assert_called_once()
        assert not target.exists()
        if preexisting:
            assert captioned.read_bytes() == b"previous captioned export"
        else:
            assert not captioned.exists()
        assert db.session.get(Clip, clip_id).editorial_status == "failed"
