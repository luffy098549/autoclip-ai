from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, Streamer, CompetitorVideo


def test_competitor_metadata_is_private_and_no_downloads():
    app=create_app({
        "TESTING": True, "WTF_CSRF_ENABLED":False,
        "SQLALCHEMY_DATABASE_URI":"sqlite://", "SECRET_KEY":"testing-only",
        "ADMIN_PASSWORD_HASH":generate_password_hash("correct-password")
    })
    with app.app_context():
        db.create_all()
        streamer=Streamer(display_name="Canal Demo",platform="youtube",channel_identifier="demo")
        db.session.add(streamer);db.session.flush()
        db.session.add(CompetitorVideo(streamer_id=streamer.id,video_id="demo123",
            title="Título de ejemplo",view_count=100,like_count=5,comment_count=1))
        db.session.commit()
        streamer_id=streamer.id
    client=app.test_client()
    assert client.get("/api/competitors/videos").status_code==401
    assert client.post(f"/api/streamers/{streamer_id}/sync").status_code==401
    client.post("/login",data={"password":"correct-password"})
    data=client.get("/api/competitors/videos").json
    assert data["items"][0]["title"]=="Título de ejemplo"
    assert client.post(f"/api/streamers/{streamer_id}/sync").status_code==503
