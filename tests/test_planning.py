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


@pytest.mark.parametrize("location", ["outside", "nested", "wrong_extension", "symlink"])
def test_planning_rejects_unmanaged_render_paths(portal, tmp_path, location):
    client, cid = portal
    sign_in(client)
    # The fixture creates its own MEDIA_ROOT; derive it from the current clip.
    from app.models import Clip, db
    from flask import current_app
    app = client.application
    with app.app_context():
        clip = db.session.get(Clip, cid)
        clips = Path(current_app.config["MEDIA_ROOT"]) / "clips"
        if location == "outside":
            target = clips.parent / "outside.mp4"
            target.write_bytes(b"test")
        elif location == "nested":
            folder = clips / "nested"
            folder.mkdir()
            target = folder / "nested.mp4"
            target.write_bytes(b"test")
        elif location == "wrong_extension":
            target = clips / "wrong.txt"
            target.write_bytes(b"test")
        else:
            original = clips.parent / "outside.mp4"
            original.write_bytes(b"test")
            target = clips / "linked.mp4"
            target.symlink_to(original)
        clip.output_path = str(target)
        db.session.commit()
    assert plan(client, cid).status_code == 400
    with app.app_context():
        assert Publication.query.count() == 0


@pytest.mark.parametrize("payload", [None, [], [1], "text", 42, True])
def test_planning_rejects_non_object_json(portal, payload):
    client, cid = portal
    sign_in(client)
    response = client.post("/api/plans", json=payload)
    assert response.status_code == 400
    assert "error" in response.json


@pytest.mark.parametrize("bad_id", [True, False, 1.5, "1.0", "-1", "1e2", [], {}, None])
def test_planning_rejects_nonintegral_clip_ids(portal, bad_id):
    client, cid = portal
    sign_in(client)
    response = client.post("/api/plans", json={
        "clip_id": bad_id, "platform": "youtube",
        "scheduled_local": "2099-10-05T10:00",
    })
    assert response.status_code == 400
    with client.application.app_context():
        assert Publication.query.count() == 0


def test_reschedule_draft_without_publishing(portal):
    client, cid = portal
    sign_in(client)
    first = plan(client, cid)
    assert first.status_code == 201
    pid = first.json["item"]["id"]
    response = client.post(f"/api/plans/{pid}/reschedule", json={
        "scheduled_local": "2099-10-05T14:00",
    })
    assert response.status_code == 200
    assert response.json["item"]["scheduled_local"] == "2099-10-05T14:00"
    assert response.json["item"]["state"] == "planned"
    assert client.get("/api/plans").json["publishing_enabled"] is False
    with client.application.app_context():
        assert Publication.query.count() == 1


def test_reschedule_rejects_conflicts_and_preserves_original(portal):
    client, cid = portal
    sign_in(client)
    first = plan(client, cid)
    second = plan(client, cid, "2099-10-05T14:00")
    assert first.status_code == second.status_code == 201
    pid = first.json["item"]["id"]
    conflict = client.post(f"/api/plans/{pid}/reschedule", json={
        "scheduled_local": "2099-10-05T13:00",
    })
    assert conflict.status_code == 409
    listing = client.get("/api/plans").json["items"]
    assert next(p for p in listing if p["id"] == pid)["scheduled_local"] == "2099-10-05T10:00"


@pytest.mark.parametrize("payload", [None, [], "bad", {}, {"scheduled_local": "2000-01-01T00:00"}])
def test_reschedule_rejects_invalid_requests(portal, payload):
    client, cid = portal
    sign_in(client)
    pid = plan(client, cid).json["item"]["id"]
    response = client.post(f"/api/plans/{pid}/reschedule", json=payload)
    assert response.status_code == 400
    assert client.get("/api/plans").json["items"][0]["scheduled_local"] == "2099-10-05T10:00"


def test_reschedule_requires_admin_and_pending_draft(portal):
    client, cid = portal
    assert client.post("/api/plans/1/reschedule", json={
        "scheduled_local": "2099-10-05T14:00",
    }).status_code == 401
    sign_in(client)
    assert client.post("/api/plans/999/reschedule", json={
        "scheduled_local": "2099-10-05T14:00",
    }).status_code == 404
    pid = plan(client, cid).json["item"]["id"]
    assert client.post(f"/api/plans/{pid}/cancel").status_code == 200
    assert client.post(f"/api/plans/{pid}/reschedule", json={
        "scheduled_local": "2099-10-05T14:00",
    }).status_code == 409
