"""Regression coverage for whole-word highlight cues."""
from app.intelligence import highlights


def _score(text, monkeypatch):
    monkeypatch.setattr(highlights, "CUES", {"wow"})
    segments = [
        {"start": i * 5.0, "end": i * 5.0 + 4.5, "text": text}
        for i in range(9)
    ]
    candidates = highlights.score_candidates(segments, max_clips=1)
    assert candidates, "Test fixture should yield a candidate"
    return candidates[0].score


def test_whole_word_cue_increases_score(monkeypatch):
    baseline = _score("today we watched a remarkable moment together", monkeypatch)
    with_cue = _score("today we watched a remarkable wow together", monkeypatch)
    assert with_cue > baseline


def test_embedded_cue_does_not_increase_score(monkeypatch):
    baseline = _score("today we watched a remarkable now together", monkeypatch)
    embedded = _score("today we watched a remarkable awow together", monkeypatch)
    assert embedded == baseline


def test_punctuation_delimits_cue(monkeypatch):
    plain = _score("today we watched a remarkable now together", monkeypatch)
    punctuated = _score("today we watched a remarkable wow, together", monkeypatch)
    assert punctuated > plain
