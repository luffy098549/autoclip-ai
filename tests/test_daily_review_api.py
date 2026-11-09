"""API integration tests for database-backed manual daily review."""
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Clip, MediaSource, db


def make_app():
    app = create_app({
        "TESTING": True, "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "review-test-only",
        "ADMIN_PASSWORD_HASH": generate_password_hash("review-test-password"),
    })
    with app.app_context():
        db.create_all()
        owned = MediaSource(source_uri="owned.mp4", rights_status="owned",
                            permission_evidence="Owner's recording")
        denied = MediaSource(source_uri="third-party.mp4", rights_status="unverified")
        db.session.add_all([owned, denied])
        db.session.flush()
        db.session.add_all([
            Clip(source_id=owned.id, start_seconds=0, end_seconds=20,
                 score=96, editorial_status="ready", output_path="a.mp4"),
            Clip(source_id=owned.id, start_seconds=10, end_seconds=30,
                 score=95, editorial_status="ready", output_path="b.mp4"),
            Clip(source_id=owned.id, start_seconds=35, end_seconds=55,
                 score=88, editorial_status="ready", output_path="c.mp4"),
            Clip(source_id=denied.id, start_seconds=0, end_seconds=20,
                 score=99, editorial_status="ready", output_path="d.mp4"),
            Clip(source_id=owned.id, start_seconds=60, end_seconds=80,
                 score=98, editorial_status="draft", output_path="e.mp4"),
            Clip(source_id=owned.id, start_seconds=85, end_seconds=105,
                 score=60, editorial_status="ready", output_path="f.mp4"),
        ])
        db.session.commit()
    return app


def test_daily_review_requires_authentication():
    client = make_app().test_client()
    assert client.get("/api/review/daily").status_code == 401


def test_daily_review_filters_rights_status_and_overlapping_clips():
    client = make_app().test_client()
    client.post("/login", data={"password": "review-test-password"})
    response = client.get("/api/review/daily")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["target"] == 5
    assert payload["count"] == 2
    assert [item["score"] for item in payload["items"]] == [96, 88]
    assert payload["publishing_enabled"] is False
    assert payload["items"][0]["download_url"].startswith("/api/clips/")


def test_daily_review_rejects_invalid_limits():
    client = make_app().test_client()
    client.post("/login", data={"password": "review-test-password"})
    for value in ("0", "21", "nope"):
        assert client.get("/api/review/daily?limit=" + value).status_code == 400
