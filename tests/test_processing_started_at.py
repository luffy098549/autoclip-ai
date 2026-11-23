"""Processing claims are timestamped only while a worker owns the clip."""
from pathlib import Path

from app import create_app
from app.models import Clip, MediaSource, db
from app.services.clip_processor import process_clip


def test_processing_timestamp_is_present_during_render_and_cleared_on_success(monkeypatch, tmp_path):
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

            def fake_render(source_uri, destination, start, end, authorized):
                db.session.expire_all()
                active = db.session.get(Clip, clip_id)
                assert active.editorial_status == "processing"
                assert active.processing_started_at is not None
                Path(destination).parent.mkdir(parents=True, exist_ok=True)
                Path(destination).write_bytes(b"synthetic test media")
                return {"path": str(destination)}

            monkeypatch.setattr("app.services.clip_processor.create_local_clip", fake_render)
            monkeypatch.setattr(
                "app.services.subtitle_export.export_clip_srt", lambda *args: None
            )
            result = process_clip(clip_id)
            db.session.expire_all()
            finished = db.session.get(Clip, clip_id)
            assert finished.editorial_status == "ready"
            assert finished.processing_started_at is None
            assert result["path"] == finished.output_path
        finally:
            db.session.remove()
            db.drop_all()
