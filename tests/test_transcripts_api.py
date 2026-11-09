from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, MediaSource, TranscriptSegment


def test_transcript_is_private_and_escapes_on_client():
    app=create_app({
        "TESTING":True,"WTF_CSRF_ENABLED":False,
        "SQLALCHEMY_DATABASE_URI":"sqlite://",
        "SECRET_KEY":"test-secret",
        "ADMIN_PASSWORD_HASH":generate_password_hash("password-test"),
    })
    with app.app_context():
        db.create_all()
        src=MediaSource(source_uri="original.mp4",rights_status="owned",
                        permission_evidence="Owned")
        db.session.add(src);db.session.flush()
        db.session.add(TranscriptSegment(
            source_id=src.id,start_seconds=1,end_seconds=3,
            text="<script>not allowed</script>",language="es"
        ))
        db.session.commit()
        src_id=src.id
    client=app.test_client()
    assert client.get(f"/api/sources/{src_id}/transcript").status_code==401
    client.post("/login",data={"password":"password-test"})
    result=client.get(f"/api/sources/{src_id}/transcript")
    assert result.status_code==200
    assert result.json["count"]==1
    assert result.json["segments"][0]["start"]==1
    # UI renders content via textContent, never raw innerHTML.
