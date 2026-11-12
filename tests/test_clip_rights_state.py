"""Revoking source rights must not overwrite reviewed or published clip states."""
from unittest.mock import patch

import pytest

from app.models import Clip, MediaSource, db
from app.services.clip_processor import process_clip
from test_clip_processor_cleanup import worker_case


@pytest.mark.parametrize(
    ("initial_status", "expected_status"),
    [
        ("draft", "rejected"),
        ("awaiting_worker", "rejected"),
        ("failed", "rejected"),
        ("processing", "processing"),
        ("ready", "ready"),
        ("approved", "approved"),
        ("published", "published"),
        ("rejected", "rejected"),
    ],
)
def test_revoked_rights_never_overwrite_protected_clip(worker_case, initial_status, expected_status):
    app, clip_id, _ = worker_case
    with app.app_context():
        clip = db.session.get(Clip, clip_id)
        clip.editorial_status = initial_status
        source = db.session.get(MediaSource, clip.source_id)
        source.rights_status = "unverified"
        source.permission_evidence = None
        db.session.commit()
        with patch("app.services.clip_processor.create_local_clip") as render:
            with pytest.raises(PermissionError, match="autorización"):
                process_clip(clip_id)
            render.assert_not_called()
        db.session.expire_all()
        assert db.session.get(Clip, clip_id).editorial_status == expected_status
