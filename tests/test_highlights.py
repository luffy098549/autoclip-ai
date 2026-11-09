from app.intelligence.highlights import score_candidates
from app.services.subtitles import build_srt


def test_finds_candidates_with_speech():
    segments = [
        {"start": n * 5.0, "end": n * 5.0 + 4.5,
         "text": ("¡Es increíble lo que pasó! Espera, mira esta reacción, "
                  "esto no puede ser real, todo está cambiando ahora mismo.")}
        for n in range(18)
    ]
    selected = score_candidates(segments)
    assert selected
    assert len(selected) <= 5
    assert all(18 <= x.end - x.start <= 65 for x in selected)
    assert all(0 <= x.score <= 100 for x in selected)


def test_sparse_or_blank_audio_returns_no_clips():
    assert score_candidates([]) == []
    assert score_candidates([{"start": 0, "end": 5, "text": "hola"}]) == []


def test_subtitle_builder_timestamps():
    srt = build_srt([{"start": 1.5, "end": 2.5, "text": "Hola mundo"}])
    assert "00:00:01,500 --> 00:00:02,500" in srt
