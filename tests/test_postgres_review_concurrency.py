"""Real PostgreSQL concurrency regression for daily review reservations.

Run by the postgres-integration CI job with DATABASE_URL set.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app import create_app
from app.models import db, Clip, MediaSource, DailyReviewSlot
from app.services.daily_review import reserve_review_slot

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL", "").startswith("postgresql"),
    reason="Requires PostgreSQL DATABASE_URL",
)


def test_concurrent_workers_never_reserve_more_than_five_slots():
    app = create_app({"TESTING": True})
    now = datetime(2026, 11, 11, 18, tzinfo=timezone.utc)
    with app.app_context():
        source = MediaSource(
            source_uri=f"synthetic-concurrency-{uuid4().hex}",
            rights_status="owned", permission_evidence="Generated CI fixture",
        )
        db.session.add(source)
        db.session.flush()
        clips = [
            Clip(source_id=source.id, start_seconds=i, end_seconds=i + 1)
            for i in range(12)
        ]
        db.session.add_all(clips)
        db.session.commit()
        source_id = source.id
        clip_ids = [clip.id for clip in clips]

    def claim(clip_id):
        with app.app_context():
            try:
                return reserve_review_slot(clip_id, now)
            finally:
                db.session.remove()

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(claim, clip_ids))
        claimed = [slot for slot in results if slot is not None]
        assert sorted(claimed) == [1, 2, 3, 4, 5]
        with app.app_context():
            rows = db.session.scalars(
                select(DailyReviewSlot).where(DailyReviewSlot.clip_id.in_(clip_ids))
            ).all()
            assert len(rows) == 5
            assert len({row.slot for row in rows}) == 5
    finally:
        with app.app_context():
            # Clean up committed fixtures in FK order.
            db.session.query(DailyReviewSlot).filter(
                DailyReviewSlot.clip_id.in_(clip_ids)
            ).delete(synchronize_session=False)
            db.session.query(Clip).filter(Clip.id.in_(clip_ids)).delete(
                synchronize_session=False
            )
            db.session.query(MediaSource).filter(MediaSource.id == source_id).delete()
            db.session.commit()
