from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db


def test_system_status_is_private_and_never_exposes_secrets(tmp_path):
    app=create_app({
        "TESTING":True,
        "SQLALCHEMY_DATABASE_URI":"sqlite://",
        "SECRET_KEY":"this-is-a-private-test-secret",
        "ADMIN_PASSWORD_HASH":generate_password_hash("unique-test-password"),
        "MEDIA_ROOT":str(tmp_path),
        "WTF_CSRF_ENABLED":False
    })
    with app.app_context():
        db.create_all()
    client=app.test_client()
    assert client.get("/api/system").status_code==401
    assert client.get("/api/summary").status_code==401
    client.post("/login",data={"password":"unique-test-password"})
    response=client.get("/api/system")
    assert response.status_code==200
    result=response.json
    assert result["database"]["dialect"]=="sqlite"
    assert result["database"]["connected"] is True
    assert result["social_publishing_enabled"] is False
    assert "SECRET_KEY" not in response.data.decode("utf-8")
    assert "this-is-a-private-test-secret" not in response.data.decode("utf-8")
    assert response.headers["X-Frame-Options"]=="DENY"
    assert response.headers["X-Content-Type-Options"]=="nosniff"
    assert response.headers["Cache-Control"]=="private, no-store"
