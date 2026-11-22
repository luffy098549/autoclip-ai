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
            with pytest.raises(ValueError, match="unexpected output path"):
                process_clip(clip_id)
            db.session.expire_all()
            saved = db.session.get(Clip, clip_id)
            assert saved.editorial_status == "failed"
            assert saved.output_path is None
            assert unrelated.read_bytes() == b"must remain intact"
            assert not (tmp_path / "clips" / f"clip-{clip_id}.mp4").exists()
        finally:
            db.session.remove()
            db.drop_all()
