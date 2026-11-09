from app import create_app
from app.models import db
from werkzeug.security import generate_password_hash


def test_ai_request_requires_configuration():
    app = create_app({
        "TESTING": True, "WTF_CSRF_ENABLED": False, "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "test-secret", "ADMIN_PASSWORD_HASH": generate_password_hash("some-test-password"),
        "AI_ENABLED": False
    })
    with app.app_context():
        db.create_all()
    client = app.test_client()
    assert client.post("/api/sources/1/analyze").status_code == 401
    assert client.post("/login", data={"password":"some-test-password"}).status_code == 302
    response = client.post("/api/sources/1/analyze")
    assert response.status_code == 503
