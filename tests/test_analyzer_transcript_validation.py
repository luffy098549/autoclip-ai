"""Transcription payloads must be rejected before partial DB persistence."""
import pytest

from app import create_app
from app.models import db, MediaSource, TranscriptSegment
from app.services.analyzer import _validate_transcription, analyze_source


@pytest.mark.parametrize("payload", [
    None, [], {}, {"language": "es", "segments": None},
    {"language": "", "segments": []},
    {"language": "x" * 21, "segments": []},
    {"language": "es", "segments": [{}]},
    {"language": "es", "segments": [{"start": 0, "end": 1, "text": None}]},
    {"language": "es", "segments": [{"start": 0, "end": 1, "text": "  "}]},
    {"language": "es", "segments": [{"start": True, "end": 1, "text": "ok"}]},
    {"language": "es", "segments": [{"start": 0, "end": float("nan"), "text": "ok"}]},
    {"language": "es", "segments": [{"start": 0, "end": float("inf"), "text": "ok"}]},
    {"language": "es", "segments": [{"start": -1, "end": 1, "text": "ok"}]},
    {"language": "es", "segments": [{"start": 2, "end": 1, "text": "ok"}]},
    {"language": "es", "segments": [{"start": 1, "end": 1, "text": "ok"}]},
    {"language": "es", "segments": [{"start": "0", "end": 1, "text": "ok"}]},
    {"language": "es", "segments": [{"start": 0, "end": 10 ** 1000, "text": "ok"}]},
    {"language": "es", "segments": [{"start": 10 ** 1000, "end": 10 ** 1001, "text": "ok"}]},
    {"language": "es", "segments": [{"start": 0, "end": 1e-320, "text": "ok"}]},
])
def test_reject_invalid_transcription(payload):
    with pytest.raises(ValueError):
        _validate_transcription(payload)


def test_valid_transcription_normalized():
    assert _validate_transcription({"language": " es ", "segments": [
        {"start": 0, "end": 1.5, "text": " hola "}
    ]}) == ("es", [(0.0, 1.5, "hola")])


def test_invalid_second_segment_does_not_persist_first(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    video = tmp_path / "owned.mp4"
    video.write_bytes(b"synthetic placeholder; transcription mocked")
    monkeypatch.setattr("app.services.analyzer.transcribe_file", lambda *a, **kw: {
        "language": "es", "segments": [
            {"start": 0, "end": 1, "text": "valid"},
            {"start": 1, "end": float("inf"), "text": "invalid"},
        ]
    })
    with app.app_context():
        db.create_all()
        source = MediaSource(source_uri=str(video), rights_status="owned",
                             permission_evidence="Original footage I created")
        db.session.add(source)
        db.session.commit()
        with pytest.raises(ValueError, match="timestamps"):
            analyze_source(source.id)
        assert TranscriptSegment.query.filter_by(source_id=source.id).count() == 0
