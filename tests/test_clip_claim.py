"""Render claims are exclusive and cannot overwrite reviewed clips."""
from unittest.mock import patch

import pytest

from app.models import db, Clip
from app.services.clip_processor import process_clip
from test_clip_processor_cleanup import worker_case  # reuse synthetic authorized fixture


@pytest.mark.parametrize("status", ["processing", "ready", "approved", "published", "rejected"])
def test_noneligible_clip_cannot_render(worker_case, status):
    app, clip_id, _ = worker_case
    with app.app_context():
        clip = db.session.get(Clip, clip_id)
        clip.editorial_status = status
        db.session.commit()
        with patch("app.services.clip_processor.create_local_clip") as render:
            with pytest.raises(RuntimeError, match="already processing or not eligible"):
                process_clip(clip_id)
            render.assert_not_called()
        db.session.expire_all()
        assert db.session.get(Clip, clip_id).editorial_status == status
