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


def test_highlights_skip_invalid_timestamps_and_large_silence():
    segments = [
        {"start": float("nan"), "end": 10, "text": "wow"},
        {"start": -3, "end": 1, "text": "wow"},
        {"start": 0, "end": 5, "text": "wow this is an amazing moment"},
        {"start": 30, "end": 35, "text": "wait no way that happened"},
    ]
    assert score_candidates(segments) == []


def test_candidate_selector_rejects_nonfinite_scores():
    from app.services.candidates import Candidate, select_candidates
    candidates = [
        Candidate(0, 30, float("nan")),
        Candidate(30, 60, float("inf")),
        Candidate(float("nan"), 60, 90),
        Candidate(60, 90, 90),
    ]
    assert select_candidates(candidates) == [Candidate(60, 90, 90)]


def test_audio_peaks_raise_reaction_score():
    segments = [
        {"start": n * 5.0, "end": n * 5.0 + 4.5,
         "text": "this is an amazing moment and the whole crowd is reacting right now"}
        for n in range(12)
    ]
    baseline = score_candidates(segments, max_clips=5)
    enhanced = score_candidates(
        segments, max_clips=5,
        audio_peaks=[(20.0, 1.0), (25.0, 1.0), (30.0, 1.0)],
    )
    assert baseline and enhanced
    assert max(x.score for x in enhanced) >= max(x.score for x in baseline)
