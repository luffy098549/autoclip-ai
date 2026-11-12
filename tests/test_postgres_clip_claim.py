"""PostgreSQL integration: only one worker can claim a clip while rendering.

Uses synthetic authorized records and mocked rendering; no third-party media.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4
from unittest.mock import patch

import pytest

from app import create_app
from app.models import db, Clip, MediaSource
from app.services.clip_processor import process_clip

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL", "").startswith("postgresql"),
    reason="Requires PostgreSQL DATABASE_URL",
)


def test_parallel_render_claim_is_exclusive(tmp_path):
    app = create_app({"TESTING": True, "MEDIA_ROOT": str(tmp_path)})
    entered_render = Event()
    release_render = Event()
    with app.app_context():
        source = MediaSource(
            source_uri=f"synthetic-claim-{uuid4().hex}.mp4",
            rights_status="owned",
            permission_evidence="Synthetic integration fixture",
        )
        db.session.add(source)
        db.session.flush()
        clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10,
                    editorial_status="awaiting_worker")
        db.session.add(clip)
        db.session.commit()
        source_id, clip_id = source.id, clip.id

    def fake_render(*args, **kwargs):
        entered_render.set()
        if not release_render.wait(timeout=15):
            raise TimeoutError("Timed out waiting for concurrent claim")
        raise RuntimeError("synthetic render failure")

    def worker():
        with app.app_context():
            try:
                return process_clip(clip_id)
            finally:
                db.session.remove()

    try:
        with patch("app.services.clip_processor.create_local_clip", side_effect=fake_render):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(worker)
                assert entered_render.wait(timeout=15), "First worker never reached render"
                second = pool.submit(worker)
                with pytest.raises(RuntimeError, match="already processing or not eligible"):
                    second.result(timeout=15)
                release_render.set()
                with pytest.raises(RuntimeError, match="synthetic render failure"):
                    first.result(timeout=15)
        with app.app_context():
            db.session.expire_all()
            assert db.session.get(Clip, clip_id).editorial_status == "failed"
    finally:
        release_render.set()
        with app.app_context():
            db.session.query(Clip).filter_by(id=clip_id).delete()
            db.session.query(MediaSource).filter_by(id=source_id).delete()
            db.session.commit()
