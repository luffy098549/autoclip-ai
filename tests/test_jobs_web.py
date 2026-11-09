from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db, Clip, MediaSource


def test_jobs_dashboard_renders_but_clip_data_stays_private():
    app=create_app({
        "TESTING":True,"WTF_CSRF_ENABLED":False,
        "SQLALCHEMY_DATABASE_URI":"sqlite://",
        "SECRET_KEY":"only-for-test",
        "ADMIN_PASSWORD_HASH":generate_password_hash("test-password"),
    })
    with app.app_context():
        db.create_all()
        source=MediaSource(source_uri="owned.mp4",rights_status="owned",
                           permission_evidence="Made by me")
        db.session.add(source)
        db.session.flush()
        db.session.add(Clip(source_id=source.id,start_seconds=1,end_seconds=20,
                            editorial_status="queued"))
        db.session.commit()
    client=app.test_client()
    assert client.get("/api/clips").status_code==401
    guest=client.get("/jobs")
    assert guest.status_code==200
    assert b"api/clips" not in guest.data
    client.post("/login",data={"password":"test-password"})
    response=client.get("/jobs")
    assert response.status_code==200
    assert b"jobs-list" in response.data
    clips=client.get("/api/clips")
    assert clips.status_code==200
    assert clips.json["items"][0]["status"]=="queued"
