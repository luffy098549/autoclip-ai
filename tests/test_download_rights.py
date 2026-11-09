"""Regression tests for owner-only downloads of authorized local clips."""
from pathlib import Path

from app.models import Clip, MediaSource, db
from tests.test_previews import make_app


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
