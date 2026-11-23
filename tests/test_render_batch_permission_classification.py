"""Batch rendering must distinguish filesystem failures from rights revocation."""
import pytest

import app as app_module
from app import create_app
from app.models import db, Clip, MediaSource
from app import tasks
from app.services import clip_processor


@pytest.mark.parametrize(
    ("error", "expected_key"),
    [
        (PermissionError("filesystem denied"), "failed_clip_ids"),
        (clip_processor.SourceAuthorizationRevoked("rights revoked"), "unauthorized_clip_ids"),
    ],
)
def test_batch_classifies_render_permission_failures(tmp_path, monkeypatch, error, expected_key):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        source = MediaSource(
            source_uri=str(tmp_path / "owned.mp4"),
            rights_status="owned",
            permission_evidence="owned original media",
        )
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10)
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id

        monkeypatch.setattr(app_module, "create_app", lambda: app)
        monkeypatch.setattr(clip_processor, "process_clip", lambda _id: (_ for _ in ()).throw(error))
        result = tasks.render_clip_batch_task([clip_id])
        assert result[expected_key] == [clip_id]
        for key in {"rendered_clip_ids", "failed_clip_ids", "skipped_clip_ids", "unauthorized_clip_ids"} - {expected_key}:
            assert result[key] == []
        db.session.remove()
        db.drop_all()
