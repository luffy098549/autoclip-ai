from pathlib import Path
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, Clip, MediaSource, Publication


@pytest.fixture()
def portal(tmp_path):
    app=create_app({
        "TESTING":True, "WTF_CSRF_ENABLED":False,
        "SQLALCHEMY_DATABASE_URI":"sqlite://",
        "SECRET_KEY":"development-test-secret-only",
        "ADMIN_PASSWORD_HASH":generate_password_hash("very-long-test-password"),
        "MEDIA_ROOT":str(tmp_path)
    })
    media=tmp_path/"clips"
    media.mkdir()
    output=media/"clip-1.mp4"
    output.write_bytes(b"placeholder")
    with app.app_context():
        db.create_all()
        source=MediaSource(source_uri="original",rights_status="owned",
                           permission_evidence="I recorded it")
        db.session.add(source);db.session.flush()
        clip=Clip(source_id=source.id,start_seconds=0,end_seconds=25,
                  editorial_status="ready",output_path=str(output))
        db.session.add(clip);db.session.commit()
        cid=clip.id
    return app.test_client(),cid


def plan(client,clip,local="2099-10-05T10:00",platform="youtube"):
    return client.post("/api/plans",json={
        "clip_id":clip,"platform":platform,"scheduled_local":local
    })


def sign_in(client):
    assert client.post("/login",data={"password":"very-long-test-password"}).status_code==302


def test_private_plans_and_no_publication(portal):
    client,cid=portal
    assert client.get("/api/plans").status_code==401
    assert plan(client,cid).status_code==401
    sign_in(client)
    result=plan(client,cid)
    assert result.status_code==201
    assert result.json["item"]["state"]=="planned"
    assert result.json["item"]["timezone"]=="America/New_York"
    listing=client.get("/api/plans").json
    assert listing["publishing_enabled"] is False
    assert len(listing["items"])==1


def test_spacing_and_daily_limit_are_per_platform(portal):
    client,cid=portal
    sign_in(client)
    assert plan(client,cid).status_code==201
    assert plan(client,cid,"2099-10-05T11:59").status_code==409
    for hour in (12,14,16,18):
        assert plan(client,cid,f"2099-10-05T{hour:02}:00").status_code==201
    assert plan(client,cid,"2099-10-05T20:00").status_code==409
    assert plan(client,cid,"2099-10-05T10:00","tiktok").status_code==201
    assert plan(client,cid,"2099-10-06T00:00").status_code==201


def test_canceled_slots_can_be_reused(portal):
    client,cid=portal
    sign_in(client)
    response=plan(client,cid)
    pid=response.json["item"]["id"]
    assert client.post(f"/api/plans/{pid}/cancel").status_code==200
    assert plan(client,cid).status_code==201
    assert client.post(f"/api/plans/{pid}/cancel").status_code==409


def test_invalid_past_and_nonexistent_clip(portal):
    client,cid=portal
    sign_in(client)
    assert plan(client,cid,"2000-01-01T10:00").status_code==400
    assert plan(client,999).status_code==400
    assert plan(client,cid,"2099-10-05T10:00","random").status_code==400
