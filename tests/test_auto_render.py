from app import create_app


def test_auto_render_flag_defaults_off():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://"})
    client=app.test_client()
    result=client.get("/api/status").json
    assert result["auto_render_enabled"] is False


def test_job_status_rejects_unauthenticated_request():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://"})
    client=app.test_client()
    assert client.get("/api/jobs/11111111-1111-4111-8111-111111111111").status_code==401
