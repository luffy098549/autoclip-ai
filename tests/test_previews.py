from pathlib import Path
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, Clip, MediaSource


def make_app(tmp_path):
    app=create_app({
        "TESTING":True,"WTF_CSRF_ENABLED":False,
        "SQLALCHEMY_DATABASE_URI":"sqlite://",
        "SECRET_KEY":"only-for-test",
        "MEDIA_ROOT":str(tmp_path),
        "ADMIN_PASSWORD_HASH":generate_password_hash("password-only-for-test"),
    })
    folder=tmp_path/"clips"
    folder.mkdir()
    video=folder/"video.mp4"
    video.write_bytes(b"synthetic-test-mp4-contents")
    with app.app_context():
        db.create_all()
        source=MediaSource(source_uri="original",rights_status="owned",
                           permission_evidence="Created by test owner")
        db.session.add(source);db.session.flush()
        clip=Clip(source_id=source.id,start_seconds=0,end_seconds=20,
                  output_path=str(video),editorial_status="ready")
        db.session.add(clip);db.session.commit()
        cid=clip.id
    return app, cid


def test_requires_login_and_supports_range(tmp_path):
    app,cid=make_app(tmp_path)
    client=app.test_client()
    url=f"/api/clips/{cid}/preview"
    assert client.get(url).status_code==401
    client.post("/login",data={"password":"password-only-for-test"})
    response=client.get(url,headers={"Range":"bytes=0-8"})
    assert response.status_code==206
    assert response.data==b"synthetic"
    assert response.headers["Cache-Control"]=="private, no-store"
    assert response.mimetype=="video/mp4"


def test_invalid_path_is_rejected(tmp_path):
    app,cid=make_app(tmp_path)
    from app.models import db, Clip
    with app.app_context():
        clip=db.session.get(Clip,cid)
        secret=tmp_path/"other.mp4"
        secret.write_bytes(b"secret")
        clip.output_path=str(secret)
        db.session.commit()
    client=app.test_client()
    client.post("/login",data={"password":"password-only-for-test"})
    assert client.get(f"/api/clips/{cid}/preview").status_code==404


def test_missing_preview_is_404(tmp_path):
    app,_=make_app(tmp_path)
    client=app.test_client()
    client.post("/login",data={"password":"password-only-for-test"})
    assert client.get("/api/clips/9999/preview").status_code==404
