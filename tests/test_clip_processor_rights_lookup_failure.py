"""Claimed render jobs recover from rights-check errors before FFmpeg starts."""
import pytest

from app import create_app
from app.models import Clip, MediaSource, db
from app.services.clip_processor import process_clip, SourceAuthorizationRevoked


@pytest.mark.parametrize("outcome", ["rights_error", "revoked"])
def test_rights_check_failure_does_not_strand_processing(tmp_path, monkeypatch, outcome):
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
            permission_evidence="original media",
        )
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=5)
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id

        def check_rights(*args):
            if outcome == "rights_error":
                raise RuntimeError("rights service unavailable")
            return type("Decision", (), {"allowed": False})()

        monkeypatch.setattr("app.services.clip_processor.assess_rights", check_rights)
        monkeypatch.setattr(
            "app.services.clip_processor.create_local_clip",
            lambda *args, **kwargs: pytest.fail("encoder must not run"),
        )
        error = RuntimeError if outcome == "rights_error" else SourceAuthorizationRevoked
        with pytest.raises(error):
            process_clip(clip_id)

        db.session.expire_all()
        saved = db.session.get(Clip, clip_id)
        assert saved.editorial_status == ("failed" if outcome == "rights_error" else "rejected")
        assert saved.output_path is None
        db.session.remove()
        db.drop_all()
