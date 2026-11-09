from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, Clip, MediaSource


def test_subtitles_are_owner_only(tmp_path):
    app=create_app({
        "TESTING":True, "WTF_CSRF_ENABLED":False, "SQLALCHEMY_DATABASE_URI":"sqlite://",
        "SECRET_KEY":"test-secret", "MEDIA_ROOT":str(tmp_path),
        "ADMIN_PASSWORD_HASH":generate_password_hash("correct-password"),
    })
    folder=tmp_path / "subtitles"
    folder.mkdir()
    (folder / "clip-1.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHola\n")
    with app.app_context():
        db.create_all()
        source=MediaSource(source_uri="local.mp4",rights_status="owned",permission_evidence="created by me")
        db.session.add(source)
        db.session.flush()
        clip=Clip(source_id=source.id,start_seconds=0,end_seconds=3,editorial_status="ready")
        db.session.add(clip)
        db.session.commit()
        cid=clip.id
    client=app.test_client()
    assert client.get(f"/api/clips/{cid}/subtitles").status_code==401
    client.post("/login",data={"password":"correct-password"})
    response=client.get(f"/api/clips/{cid}/subtitles")
    assert response.status_code==200
    assert b"Hola" in response.data
    assert client.get("/api/clips").json["items"][0]["has_subtitles"] is True
