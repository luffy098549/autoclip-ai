from app import create_app

def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    return app.test_client()

def test_dashboard_renders():
    response = client().get("/")
    assert response.status_code == 200
    assert b"AutoClip AI" in response.data

def test_sections_render():
    for path in ("/streamers", "/clips", "/publications", "/analytics", "/settings", "/jobs", "/login"):
        assert client().get(path).status_code == 200

def test_api_status_is_disabled():
    response = client().get("/api/status")
    assert response.status_code == 200
    assert response.json["publishing_enabled"] is False
    assert response.json["interval_minutes"] == 120
    assert response.json["daily_limit_per_platform"] == 5

def test_summary_before_schema_exists():
    from werkzeug.security import generate_password_hash
    app = create_app({
        "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "private-test-secret", "WTF_CSRF_ENABLED": False,
        "ADMIN_PASSWORD_HASH": generate_password_hash("private-test-password"),
    })
    portal = app.test_client()
    assert portal.get("/api/summary").status_code == 401
    assert portal.post("/login", data={"password": "private-test-password"}).status_code == 302
    response = portal.get("/api/summary")
    assert response.status_code == 200
    assert response.json["configured"] is False
