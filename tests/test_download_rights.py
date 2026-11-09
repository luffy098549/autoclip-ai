"""Regression tests for owner-only downloads of authorized local clips."""
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Clip, MediaSource, db


def make_app(tmp_path):
    app = create_app({
        "TESTING": True, "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "only-for-test", "MEDIA_ROOT": str(tmp_path),
        "ADMIN_PASSWORD_HASH": generate_password_hash("password-only-for-test"),
    })
    folder = tmp_path / "clips"
    folder.mkdir()
    video = folder / "video.mp4"
    video.write_bytes(b"synthetic-test-mp4-contents")
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri="original", rights_status="owned",
                             permission_evidence="Created by test owner")
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=20,
                    output_path=str(video), editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    return app, clip_id


def test_download_requires_login_and_sends_private_attachment(tmp_path):
    app, clip_id = make_app(tmp_path)
    client = app.test_client()
    url = f"/api/clips/{clip_id}/download"
    assert client.get(url).status_code == 401
    client.post("/login", data={"password": "password-only-for-test"})
    response = client.get(url)
    assert response.status_code == 200
    assert response.data == b"synthetic-test-mp4-contents"
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "attachment" in response.headers["Content-Disposition"]


def test_download_denied_after_source_rights_revoked(tmp_path):
    app, clip_id = make_app(tmp_path)
    with app.app_context():
        clip = db.session.get(Clip, clip_id)
        source = db.session.get(MediaSource, clip.source_id)
        source.rights_status = "unverified"
        source.permission_evidence = None
        db.session.commit()
    client = app.test_client()
    client.post("/login", data={"password": "password-only-for-test"})
    assert client.get(f"/api/clips/{clip_id}/download").status_code == 403


def test_download_rejects_non_mp4_and_outside_directory(tmp_path):
    app, clip_id = make_app(tmp_path)
    client = app.test_client()
    client.post("/login", data={"password": "password-only-for-test"})
    with app.app_context():
        clip = db.session.get(Clip, clip_id)
        wrong_extension = tmp_path / "clips" / "not-video.txt"
        wrong_extension.write_bytes(b"not-a-video")
        clip.output_path = str(wrong_extension)
        db.session.commit()
    assert client.get(f"/api/clips/{clip_id}/download").status_code == 404
    with app.app_context():
        clip = db.session.get(Clip, clip_id)
        outside = tmp_path / "private.mp4"
        outside.write_bytes(b"private")
        clip.output_path = str(outside)
        db.session.commit()
    assert client.get(f"/api/clips/{clip_id}/download").status_code == 404
