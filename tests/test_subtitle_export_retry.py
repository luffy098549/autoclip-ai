"""Subtitle exports must be safe to retry without destroying reviewed files."""
import pytest
from app import create_app
from app.models import db, Clip, MediaSource, TranscriptSegment
from app.services.subtitle_export import export_clip_srt


@pytest.fixture
def subtitle_case(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "MEDIA_ROOT": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri="owned-test.mp4", rights_status="owned",
                             permission_evidence="Synthetic test")
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=20)
        db.session.add(clip)
        db.session.add(TranscriptSegment(source_id=source.id,
                       start_seconds=1, end_seconds=4, text="Hello", language="en"))
        db.session.commit()
        yield clip.id, tmp_path / "captions.srt"
        db.session.remove()
        db.drop_all()


def test_subtitle_export_creates_file(subtitle_case):
    clip_id, path = subtitle_case
    result = export_clip_srt(clip_id, path)
    assert result == path
    assert "Hello" in path.read_text(encoding="utf-8")


def test_subtitle_export_does_not_overwrite_existing_file(subtitle_case):
    clip_id, path = subtitle_case
    path.write_text("previously reviewed captions", encoding="utf-8")
    with pytest.raises(FileExistsError):
        export_clip_srt(clip_id, path)
    assert path.read_text(encoding="utf-8") == "previously reviewed captions"
