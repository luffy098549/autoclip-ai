"""Atomicity regression tests for source analysis."""
import pytest

from app import create_app
from app.models import db, MediaSource, TranscriptSegment, Clip
from app.services.analyzer import analyze_source


def test_scoring_failure_rolls_back_new_transcript(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    video = tmp_path / "original.mp4"
    video.write_bytes(b"owned synthetic placeholder; model mocked")
    monkeypatch.setattr("app.services.analyzer.transcribe_file", lambda *args, **kwargs: {
        "language": "es", "segments": [{"start": 0, "end": 2, "text": "Hello"}]
    })
    monkeypatch.setattr("app.services.analyzer.detect_audio_peaks", lambda *args: [])
    def fail_scoring(*args, **kwargs):
        raise RuntimeError("simulated scoring failure")
    monkeypatch.setattr("app.services.analyzer.score_candidates", fail_scoring)

    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri=str(video), rights_status="owned",
                             permission_evidence="I recorded this footage")
        db.session.add(source)
        db.session.commit()
        source_id = source.id

        with pytest.raises(RuntimeError, match="scoring failure"):
            analyze_source(source_id)

        db.session.remove()  # Check persisted rows in a fresh session.
        assert TranscriptSegment.query.filter_by(source_id=source_id).count() == 0
        assert Clip.query.filter_by(source_id=source_id).count() == 0


def test_success_commits_transcript_and_clip_together(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    video = tmp_path / "original.mp4"
    video.write_bytes(b"owned synthetic placeholder; model mocked")
    monkeypatch.setattr("app.services.analyzer.transcribe_file", lambda *args, **kwargs: {
        "language": "en", "segments": [{"start": 0, "end": 4, "text": "Incredible moment and surprising result"}]
    })
    monkeypatch.setattr("app.services.analyzer.detect_audio_peaks", lambda *args: [])
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri=str(video), rights_status="owned",
                             permission_evidence="I recorded this footage")
        db.session.add(source)
        db.session.commit()
        result = analyze_source(source.id)
        db.session.remove()
        assert TranscriptSegment.query.filter_by(source_id=result["source_id"]).count() == 1
        assert Clip.query.filter_by(source_id=result["source_id"]).count() == result["candidate_count"]
