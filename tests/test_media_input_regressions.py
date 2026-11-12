"""Regressions for timestamp validation and lexical cue scoring."""
import math
from unittest.mock import patch

import pytest

from app.pipeline import create_local_clip
from app.video import render_vertical_clip
from app.intelligence.highlights import score_candidates


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_pipeline_rejects_nonfinite_timestamps_before_media_probe(bad):
    with patch("app.pipeline.inspect_video") as probe:
        with pytest.raises(ValueError):
            create_local_clip("missing.mp4", "out.mp4", start=bad, end=30, authorized=True)
        probe.assert_not_called()


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_renderer_rejects_nonfinite_end_timestamp(tmp_path, bad):
    source = tmp_path / "input.mp4"
    source.touch()
    with patch("app.video.subprocess.run") as runner:
        with pytest.raises(ValueError):
            render_vertical_clip(source, tmp_path / "output.mp4", 0, bad)
        runner.assert_not_called()


def test_cue_matches_standalone_word_not_substring():
    base = "this is a completely original story with many interesting moments and exciting details " * 3
    standalone = [{"start": 0, "end": 30, "text": "wow " + base}]
    embedded = [{"start": 0, "end": 30, "text": "wowzers " + base}]
    with_cue = score_candidates(standalone)
    without_cue = score_candidates(embedded)
    assert with_cue and without_cue
    assert with_cue[0].score > without_cue[0].score
