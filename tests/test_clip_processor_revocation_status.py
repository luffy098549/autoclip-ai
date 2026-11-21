"""Authorization revocation must not be treated as a retryable encoder failure."""
from types import SimpleNamespace

import pytest

from app import create_app
from app.models import db, Clip, MediaSource
from app.services import clip_processor, subtitle_export


@pytest.mark.parametrize(
    ("error_kind", "expected_status"),
    [("revoked", "rejected"), ("encoder", "failed")],
)
def test_render_failure_distinguishes_revoked_rights_from_encoder_errors(
    tmp_path, monkeypatch, error_kind, expected_status
):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
        "AUTO_CAPTION_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        source = MediaSource(
            source_uri=str(tmp_path / "authorized-input.mp4"),
            rights_status="owned",
            permission_evidence="owned original media",
        )
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=30)
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
        rights_checks = iter([True, error_kind != "revoked"])
        monkeypatch.setattr(
            clip_processor, "assess_rights",
            lambda *args: SimpleNamespace(allowed=next(rights_checks)),
        )
        monkeypatch.setattr(subtitle_export, "export_clip_srt", lambda *args: None)

        def fake_render(source_uri, target, **kwargs):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"test-only-render")
            if error_kind == "encoder":
                raise RuntimeError("synthetic FFmpeg failure")
            return {"path": str(target)}

        monkeypatch.setattr(clip_processor, "create_local_clip", fake_render)
        expected_error = PermissionError if error_kind == "revoked" else RuntimeError
        with pytest.raises(expected_error):
            clip_processor.process_clip(clip_id)

        db.session.expire_all()
        saved = db.session.get(Clip, clip_id)
        assert saved.editorial_status == expected_status
        assert saved.output_path is None
        assert not (tmp_path / "clips" / f"clip-{clip_id}.mp4").exists()
        db.session.remove()
        db.drop_all()
