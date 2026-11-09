from pathlib import Path
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, Clip, MediaSource


def test_owner_only_clip_download(tmp_path):
    app = create_app({
        "TESTING": True, "WTF_CSRF_ENABLED": False, "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "testing", "MEDIA_ROOT": str(tmp_path),
        "ADMIN_PASSWORD_HASH": generate_password_hash("correct-password"),
    })
    media_dir = tmp_path / "clips"
    media_dir.mkdir()
    video = media_dir / "clip-1.mp4"
    video.write_bytes(b"test-content")
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri=str(tmp_path / "owned.mp4"),
                             rights_status="owned", permission_evidence="original")
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=2,
                    output_path=str(video), editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    client = app.test_client()
    assert client.get(f"/api/clips/{clip_id}/download").status_code == 401
    client.post("/login", data={"password": "correct-password"})
    response = client.get(f"/api/clips/{clip_id}/download")
    assert response.status_code == 200
    assert response.data == b"test-content"


def test_download_rejects_paths_outside_media_directory(tmp_path):
    app = create_app({
        "TESTING": True, "WTF_CSRF_ENABLED": False, "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "testing", "MEDIA_ROOT": str(tmp_path),
        "ADMIN_PASSWORD_HASH": generate_password_hash("correct-password"),
    })
    other = tmp_path / "secret.txt"
    other.write_text("secret")
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri="source", rights_status="owned", permission_evidence="original")
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=2,
                    output_path=str(other), editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    client = app.test_client()
    client.post("/login", data={"password": "correct-password"})
    assert client.get(f"/api/clips/{clip_id}/download").status_code == 404
