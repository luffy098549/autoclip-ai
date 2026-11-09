from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db


def test_integration_readiness_is_owner_only_and_contains_no_secrets():
    app=create_app({
        "TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://",
        "SECRET_KEY":"private-test-value","WTF_CSRF_ENABLED":False,
        "ADMIN_PASSWORD_HASH":generate_password_hash("unique-test-password"),
    })
    with app.app_context():
        db.create_all()
    client=app.test_client()
    assert client.get("/api/integrations").status_code==401
    assert client.get("/integrations").status_code==200
    client.post("/login",data={"password":"unique-test-password"})
    response=client.get("/api/integrations")
    assert response.status_code==200
    assert response.json["youtube"]["automatic_publishing_enabled"] is False
    assert response.json["tiktok"]["developer_audit_confirmed"] is False
    assert b"private-test-value" not in response.data
