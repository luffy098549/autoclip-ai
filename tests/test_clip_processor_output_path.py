"""Renderer must not substitute an arbitrary output path for a clip artifact."""
from pathlib import Path

import pytest

from app import create_app
from app.models import Clip, MediaSource, db
from app.services.clip_processor import process_clip


def test_renderer_cannot_replace_clip_path_with_unrelated_file(monkeypatch, tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
        "AUTO_CAPTION_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        try:
            source = MediaSource(
                source_uri=str(tmp_path / "owned.mp4"),
                rights_status="owned",
                permission_evidence="original recording owned by operator",
            )
            db.session.add(source)
            db.session.flush()
            clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10,
                        editorial_status="awaiting_worker")
            db.session.add(clip)
            db.session.commit()
            clip_id = clip.id
            unrelated = tmp_path / "unrelated.mp4"
            unrelated.write_bytes(b"must remain intact")

            def wrong_path(source_uri, destination, start, end, authorized):
                Path(destination).parent.mkdir(parents=True, exist_ok=True)
                Path(destination).write_bytes(b"rendered")
                return {"path": str(unrelated)}

            monkeypatch.setattr(
                "app.services.clip_processor.create_local_clip", wrong_path
            )
            def subtitle_export_must_not_run(*args, **kwargs):
                pytest.fail("Subtitle export ran before renderer path validation")

            monkeypatch.setattr(
                "app.services.subtitle_export.export_clip_srt",
                subtitle_export_must_not_run,
            )
            with pytest.raises(ValueError, match="unexpected output path"):
                process_clip(clip_id)
            db.session.expire_all()
            saved = db.session.get(Clip, clip_id)
            assert saved.editorial_status == "failed"
            assert saved.output_path is None
            assert saved.processing_started_at is None
            assert unrelated.read_bytes() == b"must remain intact"
            assert not (tmp_path / "clips" / f"clip-{clip_id}.mp4").exists()
        finally:
            db.session.remove()
            db.drop_all()


@pytest.mark.parametrize("start,end", [
    (-1, 10), (10, 10), (11, 10),
    (0, float("inf")), (float("-inf"), 10),
])
def test_invalid_clip_interval_does_not_claim_or_render(monkeypatch, tmp_path, start, end):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        try:
            source = MediaSource(source_uri="owned.mp4", rights_status="owned",
                                 permission_evidence="original recording")
            db.session.add(source)
            db.session.flush()
            clip = Clip(source_id=source.id, start_seconds=start, end_seconds=end,
                        editorial_status="awaiting_worker")
            db.session.add(clip)
            db.session.commit()
            clip_id = clip.id

            def must_not_render(*args, **kwargs):
                pytest.fail("Invalid interval reached the renderer")

            monkeypatch.setattr("app.services.clip_processor.create_local_clip",
                                must_not_render)
            with pytest.raises(ValueError, match="Invalid clip start/end times"):
                process_clip(clip_id)
            db.session.expire_all()
            saved = db.session.get(Clip, clip_id)
            assert saved.editorial_status == "awaiting_worker"
            assert saved.processing_started_at is None
            assert saved.output_path is None
        finally:
            db.session.remove()
            db.drop_all()


@pytest.mark.parametrize("write_empty", [False, True])
def test_renderer_must_produce_nonempty_artifact(monkeypatch, tmp_path, write_empty):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        try:
            source = MediaSource(
                source_uri="owned.mp4", rights_status="owned",
                permission_evidence="original recording owned by operator",
            )
            db.session.add(source)
            db.session.flush()
            clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10,
                        editorial_status="awaiting_worker")
            db.session.add(clip)
            db.session.commit()
            clip_id = clip.id

            def missing_or_empty_artifact(source_uri, destination, start, end, authorized):
                if write_empty:
                    Path(destination).parent.mkdir(parents=True, exist_ok=True)
                    Path(destination).write_bytes(b"")
                return {"path": str(destination)}

            def must_not_export(*args, **kwargs):
                pytest.fail("Subtitle export ran for a missing or empty render")

            monkeypatch.setattr(
                "app.services.clip_processor.create_local_clip", missing_or_empty_artifact
            )
            monkeypatch.setattr(
                "app.services.subtitle_export.export_clip_srt", must_not_export
            )
            with pytest.raises(ValueError, match="nonempty clip artifact"):
                process_clip(clip_id)
            db.session.expire_all()
            saved = db.session.get(Clip, clip_id)
            assert saved.editorial_status == "failed"
            assert saved.processing_started_at is None
            assert saved.output_path is None
            assert not (tmp_path / "clips" / f"clip-{clip_id}.mp4").exists()
        finally:
            db.session.remove()
            db.drop_all()


@pytest.mark.parametrize("empty_caption", [False, True])
def test_caption_renderer_requires_nonempty_output(monkeypatch, tmp_path, empty_caption):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
        "AUTO_CAPTION_ENABLED": True,
    })
    with app.app_context():
        db.create_all()
        try:
            source = MediaSource(
                source_uri="owned.mp4", rights_status="owned",
                permission_evidence="original recording owned by operator",
            )
            db.session.add(source)
            db.session.flush()
            clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10,
                        editorial_status="awaiting_worker")
            db.session.add(clip)
            db.session.commit()
            clip_id = clip.id

            def render(source_uri, destination, start, end, authorized):
                Path(destination).parent.mkdir(parents=True, exist_ok=True)
                Path(destination).write_bytes(b"synthetic clip")
                return {"path": str(destination)}

            def export_srt(clip_id, destination):
                Path(destination).parent.mkdir(parents=True, exist_ok=True)
                Path(destination).write_text("1\\n00:00:00,000 --> 00:00:01,000\\nTest\\n")
                return str(destination)

            def burn(source_path, subtitle_path, destination):
                if empty_caption:
                    Path(destination).write_bytes(b"")
                return str(destination)

            monkeypatch.setattr("app.services.clip_processor.create_local_clip", render)
            monkeypatch.setattr("app.services.subtitle_export.export_clip_srt", export_srt)
            monkeypatch.setattr("app.services.caption_burn.burn_subtitles", burn)

            with pytest.raises(ValueError, match="Caption renderer.*nonempty"):
                process_clip(clip_id)
            db.session.expire_all()
            saved = db.session.get(Clip, clip_id)
            assert saved.editorial_status == "failed"
            assert saved.output_path is None
            assert saved.processing_started_at is None
            assert not (tmp_path / "clips" / f"clip-{clip_id}.mp4").exists()
            assert not (tmp_path / "clips" / f"clip-{clip_id}-captioned.mp4").exists()
            assert not (tmp_path / "subtitles" / f"clip-{clip_id}.srt").exists()
        finally:
            db.session.remove()
            db.drop_all()


@pytest.mark.parametrize("captioned_output", [False, True])
def test_renderer_symlink_cannot_expose_external_media(monkeypatch, tmp_path, captioned_output):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
        "AUTO_CAPTION_ENABLED": captioned_output,
    })
    with app.app_context():
        db.create_all()
        try:
            source = MediaSource(
                source_uri="owned.mp4", rights_status="owned",
                permission_evidence="original recording owned by operator",
            )
            db.session.add(source)
            db.session.flush()
            clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10,
                        editorial_status="awaiting_worker")
            db.session.add(clip)
            db.session.commit()
            clip_id = clip.id
            external = tmp_path / "private-external.mp4"
            external.write_bytes(b"private data must remain untouched")

            def render(source_uri, destination, start, end, authorized):
                destination = Path(destination)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if captioned_output:
                    destination.write_bytes(b"synthetic owned clip")
                else:
                    destination.symlink_to(external)
                return {"path": str(destination)}

            def export_srt(clip_id, destination):
                destination = Path(destination)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text("1\\n00:00:00,000 --> 00:00:01,000\\nTest\\n")
                return str(destination)

            def burn(source_path, subtitle_path, destination):
                Path(destination).symlink_to(external)
                return str(destination)

            monkeypatch.setattr("app.services.clip_processor.create_local_clip", render)
            monkeypatch.setattr("app.services.subtitle_export.export_clip_srt", export_srt)
            monkeypatch.setattr("app.services.caption_burn.burn_subtitles", burn)
            with pytest.raises(ValueError, match="nonempty .*artifact"):
                process_clip(clip_id)
            db.session.expire_all()
            saved = db.session.get(Clip, clip_id)
            assert saved.editorial_status == "failed"
            assert saved.output_path is None
            assert saved.processing_started_at is None
            assert external.read_bytes() == b"private data must remain untouched"
            assert not (tmp_path / "clips" / f"clip-{clip_id}.mp4").exists()
            assert not (tmp_path / "clips" / f"clip-{clip_id}-captioned.mp4").exists()
        finally:
            db.session.remove()
            db.drop_all()
