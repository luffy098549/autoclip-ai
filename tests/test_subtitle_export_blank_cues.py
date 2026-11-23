"""SRT export must not create unusable sidecars for blank transcripts."""
import pytest

from app import create_app
from app.models import Clip, MediaSource, TranscriptSegment, db
from app.services.subtitle_export import export_clip_srt


@pytest.mark.parametrize(
    ("texts", "expected_cues"),
    [
        ([" ", "\n\t"], 0),
        (["\x00", " \x00 "], 0),
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

def test_export_replace_failure_preserves_existing_sidecar(tmp_path, monkeypatch):
    from app.services import subtitle_export

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
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10)
        db.session.add_all([
            clip,
            TranscriptSegment(
                source_id=source.id, start_seconds=1,
                end_seconds=3, text="New subtitle",
            ),
        ])
        db.session.commit()
        destination = tmp_path / "clip.srt"
        destination.write_text("previous valid content", encoding="utf-8")

        def fail_replace(source_path, destination_path):
            assert destination_path == destination
            assert source_path.read_text(encoding="utf-8")
            raise OSError("simulated replacement failure")

        monkeypatch.setattr(subtitle_export.os, "replace", fail_replace)
        with pytest.raises(OSError, match="simulated replacement failure"):
            export_clip_srt(clip.id, destination)
        assert destination.read_text(encoding="utf-8") == "previous valid content"
        assert not list(tmp_path.glob(".autoclip-srt-*"))
        db.session.remove()
        db.drop_all()


def test_blank_submillisecond_segment_does_not_block_valid_cue(tmp_path):
    """An unusable blank cue must not fail the export of valid speech."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        try:
            source = MediaSource(
                source_uri=str(tmp_path / "owned.mp4"),
                rights_status="owned",
                permission_evidence="original media",
            )
            db.session.add(source)
            db.session.flush()
            clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10)
            db.session.add_all([
                clip,
                TranscriptSegment(
                    source_id=source.id, start_seconds=0,
                    end_seconds=0.0001, text=" \x00 ",
                ),
                TranscriptSegment(
                    source_id=source.id, start_seconds=1,
                    end_seconds=3, text="Valid speech",
                ),
            ])
            db.session.commit()
            destination = tmp_path / "clip.srt"
            assert export_clip_srt(clip.id, destination) == destination
            content = destination.read_text(encoding="utf-8")
            assert "Valid speech" in content
            assert content.count(" --> ") == 1
        finally:
            db.session.remove()
            db.drop_all()


def test_nonblank_submillisecond_segment_is_skipped_without_losing_valid_speech(tmp_path):
    """Tiny transcribed fragments must not invalidate the whole SRT."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        try:
            source = MediaSource(
                source_uri=str(tmp_path / "owned.mp4"),
                rights_status="owned",
                permission_evidence="original media",
            )
            db.session.add(source)
            db.session.flush()
            clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10)
            db.session.add_all([
                clip,
                TranscriptSegment(
                    source_id=source.id, start_seconds=0,
                    end_seconds=0.0001, text="tiny",
                ),
                TranscriptSegment(
                    source_id=source.id, start_seconds=1,
                    end_seconds=3, text="Full sentence",
                ),
            ])
            db.session.commit()
            destination = tmp_path / "clip.srt"
            assert export_clip_srt(clip.id, destination) == destination
            content = destination.read_text(encoding="utf-8")
            assert "Full sentence" in content
            assert "tiny" not in content
            assert content.count(" --> ") == 1
        finally:
            db.session.remove()
            db.drop_all()
