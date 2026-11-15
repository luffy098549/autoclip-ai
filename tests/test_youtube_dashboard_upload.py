"""Dashboard YouTube upload tests: no external API calls or credentials."""
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Clip, MediaSource, Publication, db


@pytest.fixture
def upload_env(tmp_path, monkeypatch):
    root = tmp_path / "storage"
    (root / "clips").mkdir(parents=True)
    (root / "private").mkdir(parents=True)
    (root / "private" / "youtube-token.json").write_text("fake-token-never-used")
    video = root / "clips" / "clip-1.mp4"
    video.write_bytes(b"mock-video-file")
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "test-only-session-key",
        "WTF_CSRF_ENABLED": False,
        "ADMIN_PASSWORD_HASH": generate_password_hash("test-password"),
        "MEDIA_ROOT": str(root),
    })
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri=str(video), rights_status="owned",
                             permission_evidence="Original video created for this test")
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=15,
                    editorial_status="ready", output_path=str(video))
        db.session.add(clip)
        db.session.commit()
    monkeypatch.setattr("app.quality.validate_render",
                        lambda path: {"duration": 15, "width": 1080, "height": 1920, "has_audio": True})
    return app, app.test_client()


def payload(**changes):
    result = {"clip_id": 1, "title": "Private integration test",
              "description": "Synthetic test media", "made_for_kids": False,
              "confirm_private": True}
    result.update(changes)
    return result


def authenticate(client):
    response = client.post("/login", data={"password": "test-password"})
    assert response.status_code in (302, 303)


def test_upload_requires_login_and_explicit_confirmation(upload_env, monkeypatch):
    app, client = upload_env
    assert client.post("/api/integrations/youtube/upload-private", json=payload()).status_code == 401
    authenticate(client)
    assert client.post("/api/integrations/youtube/upload-private",
                       json=payload(confirm_private=False)).status_code == 400
    assert client.post("/api/integrations/youtube/upload-private",
                       json=payload(made_for_kids="false")).status_code == 400
    assert client.post("/api/integrations/youtube/upload-private",
                       json=payload(title="")).status_code == 400
    with app.app_context():
        assert Publication.query.count() == 0


def test_private_upload_records_history_and_blocks_duplicates(upload_env, monkeypatch):
    app, client = upload_env
    authenticate(client)
    calls = []
    def fake_upload(video_path, title, description, **kwargs):
        calls.append((video_path, title, description, kwargs))
        return "test-video-id"
    monkeypatch.setattr("app.publishers.youtube.upload_short", fake_upload)
    response = client.post("/api/integrations/youtube/upload-private", json=payload())
    assert response.status_code == 201
    assert response.json["privacy_requested"] == "private"
    assert response.json["video_id"] == "test-video-id"
    assert calls[0][3]["privacy_status"] == "private"
    assert calls[0][3]["made_for_kids"] is False
    assert client.post("/api/integrations/youtube/upload-private", json=payload()).status_code == 409
    assert len(calls) == 1
    history = client.get("/api/integrations/youtube/uploads")
    assert history.status_code == 200
    assert history.json["items"][0]["video_id"] == "test-video-id"
    assert "fake-token" not in history.get_data(as_text=True)
    with app.app_context():
        assert Publication.query.count() == 1
        assert Publication.query.first().state == "published"


def test_uncertain_upload_never_retries_automatically(upload_env, monkeypatch):
    app, client = upload_env
    authenticate(client)
    attempts = []
    def broken_upload(*args, **kwargs):
        attempts.append(1)
        raise RuntimeError("simulated transport failure")
    monkeypatch.setattr("app.publishers.youtube.upload_short", broken_upload)
    assert client.post("/api/integrations/youtube/upload-private", json=payload()).status_code == 502
    assert client.post("/api/integrations/youtube/upload-private", json=payload()).status_code == 409
    assert len(attempts) == 1
    with app.app_context():
        assert Publication.query.first().state == "upload_uncertain"


def test_upload_rejects_unverified_rights_and_read_only_mode(upload_env, monkeypatch):
    app, client = upload_env
    authenticate(client)
    with app.app_context():
        source = MediaSource.query.first()
        source.rights_status = "unverified"
        db.session.commit()
    assert client.post("/api/integrations/youtube/upload-private", json=payload()).status_code == 403
    with app.app_context():
        assert Publication.query.count() == 0
    app.config["READ_ONLY_DEPLOYMENT"] = True
    assert client.post("/api/integrations/youtube/upload-private", json=payload()).status_code == 403
