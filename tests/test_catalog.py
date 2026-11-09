import io
from pathlib import Path
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db


def app_client(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "unit-testing-only",
        "ADMIN_PASSWORD_HASH": generate_password_hash("a-secure-unit-test-password"),
        "MEDIA_ROOT": str(tmp_path),
        "PROCESSING_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
    return app.test_client()


def sign_in(client):
    response = client.post("/login", data={"password": "a-secure-unit-test-password"})
    assert response.status_code == 302


def test_catalog_private_and_login(tmp_path):
    client = app_client(tmp_path)
    assert client.get("/api/streamers").status_code == 401
    assert client.post("/api/streamers", json={"name":"x"}).status_code == 401
    sign_in(client)
    assert client.get("/api/streamers").status_code == 200


def test_create_and_list_streamers(tmp_path):
    client = app_client(tmp_path)
    sign_in(client)
    response = client.post("/api/streamers", json={"name":"Creador Demo","platform":"kick","channel":"creador_demo"})
    assert response.status_code == 201
    assert len(client.get("/api/streamers").json["items"]) == 1
    assert client.post("/api/streamers", json={"name":"Creador Demo","platform":"kick","channel":"creador_demo"}).status_code == 409


def test_reject_unlicensed_upload(tmp_path):
    client = app_client(tmp_path)
    sign_in(client)
    response = client.post("/api/sources", data={
        "file": (io.BytesIO(b"not a video"), "demo.mp4"),
        "rights": "unverified", "evidence": ""
    }, content_type="multipart/form-data")
    assert response.status_code == 403
    assert list(Path(tmp_path).rglob("*.mp4")) == []


def test_reject_nonvideo_upload(tmp_path):
    client = app_client(tmp_path)
    sign_in(client)
    response = client.post("/api/sources", data={
        "file": (io.BytesIO(b"fake"), "data.txt"),
        "rights": "owned", "evidence": "File recorded by owner"
    }, content_type="multipart/form-data")
    assert response.status_code == 400


def test_clips_require_existing_source(tmp_path):
    client = app_client(tmp_path)
    sign_in(client)
    response = client.post("/api/clips", json={"source_id":888,"start":0,"end":20})
    assert response.status_code == 404


def test_logout_invalidates_session(tmp_path):
    client = app_client(tmp_path)
    sign_in(client)
    assert client.post("/logout").status_code == 302
    assert client.get("/api/sources").status_code == 401
