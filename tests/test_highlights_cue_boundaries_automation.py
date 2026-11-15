"""Regression tests for cue-word boundaries in highlight scoring."""
from app.intelligence import highlights
from app.intelligence.highlights import score_candidates


import pytest


@pytest.fixture(autouse=True)
def inspect_all_candidates(monkeypatch):
    """Inspect raw heuristic scores before threshold-based selection."""
    monkeypatch.setattr(highlights, "select_candidates", lambda candidates, **kwargs: candidates)


def _score(text):
    # At least 20 words are required before scoring a candidate.
    filler = " ".join(["ordinary"] * 22)
    segments = [{"start": 0, "end": 30, "text": filler + " " + text}]
    candidates = score_candidates(segments, minimum_seconds=18, maximum_seconds=65)
    assert len(candidates) == 1
    return candidates[0].score


def test_whole_word_cue_increases_score():
    assert _score("wow") > _score("plain")


def test_embedded_cue_does_not_increase_score():
    assert _score("wowzers") == _score("plainly")


def test_cue_followed_by_punctuation_is_recognized():
    # Compare punctuation-matched cues without introducing expression bonuses.
    assert _score("(wow)") > _score("(plain)")


def test_phrase_cue_respects_word_boundaries():
    assert _score("no way") > _score("snow ways")
