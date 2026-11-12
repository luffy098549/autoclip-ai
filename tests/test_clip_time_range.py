"""Invalid clip timestamps must never start a render or claim a worker slot."""
import math
from unittest.mock import patch

import pytest

from app.models import Clip, db
from app.services.clip_processor import process_clip
from test_clip_processor_cleanup import worker_case


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (-1.0, 5.0),
        (10.0, 10.0),
        (11.0, 10.0),
        (math.nan, 10.0),
        (0.0, math.nan),
        (math.inf, 10.0),
        (0.0, math.inf),
        (-math.inf, 10.0),
    ],
)
def test_invalid_range_rejected_before_claim(worker_case, start, end):
    app, clip_id, _ = worker_case
    with app.app_context():
        clip = db.session.get(Clip, clip_id)
        clip.start_seconds = start
        clip.end_seconds = end
        db.session.commit()
        with patch("app.services.clip_processor.create_local_clip") as render:
            with pytest.raises(ValueError, match="Invalid clip time range"):
                process_clip(clip_id)
            render.assert_not_called()
        db.session.expire_all()
        assert db.session.get(Clip, clip_id).editorial_status == "awaiting_worker"
