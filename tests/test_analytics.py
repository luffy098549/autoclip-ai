from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, MediaSource, Clip
from app.analytics.metrics import engagement_percent


def test_engagement_zero_views():
    assert engagement_percent(0, 50, 0, 0) == 0


def test_store_and_update_manual_snapshot():
    app=create_app({"TESTING":True,"WTF_CSRF_ENABLED":False,
                    "SQLALCHEMY_DATABASE_URI":"sqlite://",
                    "SECRET_KEY":"testing-only",
                    "ADMIN_PASSWORD_HASH":generate_password_hash("correct-password")})
    with app.app_context():
        db.create_all()
        src=MediaSource(source_uri="owned.mp4",rights_status="owned",permission_evidence="original")
        db.session.add(src);db.session.flush()
        clip=Clip(source_id=src.id,start_seconds=0,end_seconds=20)
        db.session.add(clip);db.session.commit()
        clip_id=clip.id
    client=app.test_client()
    assert client.get("/api/analytics").status_code==401
    assert client.post("/api/analytics",json={"clip_id":clip_id}).status_code==401
    client.post("/login",data={"password":"correct-password"})
    metric={"clip_id":clip_id,"platform":"youtube","views":1000,"likes":100,"comments":10,"shares":5}
    assert client.post("/api/analytics",json=metric).status_code==201
    result=client.get("/api/analytics").json
    assert result["summary"]["views"]==1000
    assert result["items"][0]["engagement_percent"]==11.5
    metric["views"]=2000
    assert client.post("/api/analytics",json=metric).status_code==201
    result=client.get("/api/analytics").json
    assert result["summary"]["views"]==2000
    assert len(result["items"])==1


def test_reject_nonexistent_metric_clip():
    app=create_app({"TESTING":True,"WTF_CSRF_ENABLED":False,
                    "SQLALCHEMY_DATABASE_URI":"sqlite://",
                    "SECRET_KEY":"testing-only",
                    "ADMIN_PASSWORD_HASH":generate_password_hash("correct-password")})
    with app.app_context():
        db.create_all()
    client=app.test_client()
    client.post("/login",data={"password":"correct-password"})
    assert client.post("/api/analytics",json={"clip_id":999,"platform":"youtube",
                        "views":42}).status_code==404
