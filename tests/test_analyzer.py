from app import create_app
from app.models import db, MediaSource, TranscriptSegment
from app.services.analyzer import analyze_source


def test_analysis_stores_transcript_and_shortlists(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    video = tmp_path / "owned.mp4"
    video.write_bytes(b"placeholder input used for transcript mock")
    def fake_transcription(path, model_size="small"):
        return {"language": "es", "segments": [
            {"start": i * 5.0, "end": i * 5.0 + 4.5,
             "text": "¡Increíble! Espera, mira esto, es una historia muy sorprendente con muchos detalles."}
            for i in range(10)
        ]}
    monkeypatch.setattr("app.services.analyzer.transcribe_file", fake_transcription)
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri=str(video), rights_status="owned",
                             permission_evidence="Original footage I created")
        db.session.add(source)
        db.session.commit()
        sid = source.id
        first = analyze_source(sid)
        assert first["transcript_segments"] == 10
        assert first["candidate_count"] >= 1
        second = analyze_source(sid)
        assert first["clip_ids"] == second["clip_ids"]
        assert TranscriptSegment.query.filter_by(source_id=sid).count() == 10


import pytest


@pytest.mark.parametrize("source_id", [None, True, False, 0, -1, 1.0, "1", [], {}])
def test_analyzer_rejects_invalid_source_id_before_db(source_id):
    with pytest.raises(ValueError, match="source_id"):
        analyze_source(source_id)


@pytest.mark.parametrize("max_clips", [None, True, False, 0, -1, 6, 1.0, 5.0, "5", [], {}])
def test_analyzer_rejects_invalid_max_clips_before_db(max_clips):
    with pytest.raises(ValueError, match="max_clips"):
        analyze_source(1, max_clips=max_clips)
