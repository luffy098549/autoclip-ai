"""Regression tests for authenticated clip requests and subtitle file confinement."""
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Clip, MediaSource, db


@pytest.fixture
def portal(tmp_path):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "test-secret-for-regressions",
        "ADMIN_PASSWORD_HASH": generate_password_hash("long-test-password"),
        "MEDIA_ROOT": str(tmp_path),
        "PROCESSING_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri=str(tmp_path / "owned.mp4"),
                             rights_status="owned",
                             permission_evidence="Recorded by test operator")
        db.session.add(source)
        db.session.commit()
        source_id = source.id
    client = app.test_client()
    assert client.post("/login", data={"password": "long-test-password"}).status_code == 302
    return app, client, source_id, tmp_path


@pytest.mark.parametrize("payload", [
    None, [], "bad", 42, True,
    {"source_id": True, "start": 0, "end": 5},
    {"source_id": 1.5, "start": 0, "end": 5},
    {"source_id": "-1", "start": 0, "end": 5},
    {"source_id": "1e2", "start": 0, "end": 5},
    {"source_id": 1, "start": True, "end": 5},
    {"source_id": 1, "start": 0, "end": False},
    {"source_id": 1, "start": "0", "end": 5},
    {"source_id": 1, "start": 0, "end": "5"},
    {"source_id": 1, "start": 10**1000, "end": 5},
])
def test_invalid_clip_payload_does_not_create_clip(portal, payload):
    app, client, _, _ = portal
    response = client.post("/api/clips", json=payload)
    assert response.status_code == 400
    with app.app_context():
        assert Clip.query.count() == 0


def test_valid_clip_request_queues_without_broker(portal, monkeypatch):
    app, client, source_id, _ = portal
    monkeypatch.setattr("app.routes.api.inspect_video",
                        lambda path: {"duration": 30, "has_audio": True})
    response = client.post("/api/clips", json={
        "source_id": source_id, "start": 0, "end": 15,
    })
    assert response.status_code == 202
    assert response.json["status"] == "awaiting_worker"
    with app.app_context():
        assert Clip.query.count() == 1


def test_subtitle_download_denies_symlink_escape(portal):
    app, client, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    subtitles = root / "subtitles"
    subtitles.mkdir()
    outside = root / "private.srt"
    outside.write_text("PRIVATE", encoding="utf-8")
    (subtitles / f"clip-{clip_id}.srt").symlink_to(outside)
    response = client.get(f"/api/clips/{clip_id}/subtitles")
    assert response.status_code == 404
    assert b"PRIVATE" not in response.data


def test_subtitle_download_is_private_and_no_store(portal):
    app, client, source_id, root = portal
    with app.app_context():
        clip = Clip(source_id=source_id, start_seconds=0, end_seconds=5,
                    editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        clip_id = clip.id
    subtitles = root / "subtitles"
    subtitles.mkdir()
    (subtitles / f"clip-{clip_id}.srt").write_text(
        "1\\n00:00:00,000 --> 00:00:01,000\\nTest\\n", encoding="utf-8"
    )
    response = client.get(f"/api/clips/{clip_id}/subtitles")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"
