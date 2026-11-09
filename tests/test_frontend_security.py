"""Browser asset availability, CSRF and authentication smoke checks."""
import re

from werkzeug.security import generate_password_hash

from app import create_app


def test_web_assets_served_without_build_step():
    app=create_app({
        "TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://",
        "SECRET_KEY":"test-secret"
    })
    client=app.test_client()
    for filename in (
        "app.js","catalog.js","planning.js","library.js",
        "system.js","jobs.js","analytics-charts.js",
    ):
        response=client.get("/static/js/"+filename)
        assert response.status_code==200, filename
        assert "javascript" in response.mimetype
    for filename in ("style.css","forms.css","planning.css",
                     "library.css","system.css","jobs.css","analytics-charts.css"):
        response=client.get("/static/css/"+filename)
        assert response.status_code==200, filename
        assert response.mimetype=="text/css"


def test_login_and_write_endpoints_enforce_csrf():
    app=create_app({
        "TESTING":True,
        "SQLALCHEMY_DATABASE_URI":"sqlite://",
        "SECRET_KEY":"private-session-secret",
        "ADMIN_PASSWORD_HASH":generate_password_hash("test-owner-password"),
    })
    client=app.test_client()
    assert client.post("/login",data={"password":"test-owner-password"}).status_code==400
    page=client.get("/login")
    token=re.search(r'name="csrf_token" value="([^"]+)"',page.data.decode()).group(1)
    response=client.post("/login",data={
        "password":"test-owner-password","csrf_token":token,
    })
    assert response.status_code==302
    assert client.post("/api/plans",json={}).status_code==400
    dashboard=client.get("/")
    token=re.search(r'name="csrf-token" content="([^"]+)"',
                    dashboard.data.decode()).group(1)
    invalid=client.post("/api/plans",json={},headers={"X-CSRFToken":token})
    assert invalid.status_code==400
    assert invalid.is_json
    assert "Selecciona" in invalid.json["error"]
