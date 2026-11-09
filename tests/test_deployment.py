from app import create_app, normalized_database_url


def test_render_postgresql_driver_normalization():
    assert normalized_database_url("postgresql://someone:pwd@host/db") == (
        "postgresql+psycopg://someone:pwd@host/db"
    )
    assert normalized_database_url("sqlite://") == "sqlite://"
    assert normalized_database_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"


def test_read_only_deployment_rejects_all_api_mutations_before_auth():
    app=create_app({
        "TESTING":True,
        "SQLALCHEMY_DATABASE_URI":"sqlite://",
        "READ_ONLY_DEPLOYMENT":True,
        "WTF_CSRF_ENABLED":False,
    })
    client=app.test_client()
    assert client.get("/health").status_code==200
    assert client.get("/api/status").json["ingestion_enabled"] is False
    for path in ("/api/sources", "/api/streamers", "/api/clips", "/api/plans", "/api/analytics"):
        response=client.post(path,json={})
        assert response.status_code==403
        assert "solo lectura" in response.json["error"]
