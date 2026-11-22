"""SRT export must not create unusable sidecars for blank transcripts."""
import pytest

from app import create_app
from app.models import Clip, MediaSource, TranscriptSegment, db
from app.services.subtitle_export import export_clip_srt


@pytest.mark.parametrize(
    ("texts", "expected_cues"),
    [
        ([" ", "\n\t"], 0),
        ([" ", "Hello there", "\n"], 1),
    ],
)
def test_export_skips_blank_transcripts(tmp_path, texts, expected_cues):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        source = MediaSource(
            source_uri=str(tmp_path / "owned.mp4"),
            rights_status="owned",
            permission_evidence="original media",
        )
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=20)
        db.session.add(clip)
        for index, text in enumerate(texts):
            db.session.add(TranscriptSegment(
                source_id=source.id,
                start_seconds=index * 2,
                end_seconds=index * 2 + 1,
                text=text,
            ))
        db.session.commit()
        destination = tmp_path / "subtitles" / "clip.srt"
        result = export_clip_srt(clip.id, destination)
        if expected_cues == 0:
            assert result is None
            assert not destination.exists()
        else:
            assert result == destination
            text = destination.read_text(encoding="utf-8")
            assert "Hello there" in text
            assert text.count(" --> ") == expected_cues
        db.session.remove()
        db.drop_all()
