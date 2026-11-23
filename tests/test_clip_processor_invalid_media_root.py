"""Invalid render output configuration must not strand claimed jobs."""
import pytest

from app import create_app
from app.models import Clip, MediaSource, db
from app.services.clip_processor import process_clip


def test_invalid_media_root_does_not_claim_clip(tmp_path):
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
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=5)
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id

        app.config["MEDIA_ROOT"] = None
        with pytest.raises(TypeError):
            process_clip(clip_id)

        db.session.expire_all()
        saved = db.session.get(Clip, clip_id)
        assert saved.editorial_status == "draft"
        assert saved.output_path is None
        db.session.remove()
        db.drop_all()
