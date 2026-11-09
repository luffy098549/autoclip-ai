"""Daily review slots are durable and database-constrained."""
from datetime import date
import pytest
from flask_migrate import upgrade
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.models import db, Clip, MediaSource, DailyReviewSlot


def test_daily_review_quota_is_persistent_and_enforced(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "review.sqlite"),
        "SECRET_KEY": "test-only",
    })
    with app.app_context():
        upgrade()
        source = MediaSource(source_uri="local-authorized-test", rights_status="authorized")
        db.session.add(source)
        db.session.flush()
        clips = [
            Clip(source_id=source.id, start_seconds=i * 30, end_seconds=(i + 1) * 30)
            for i in range(7)
        ]
        db.session.add_all(clips)
        db.session.commit()
        day = date(2026, 11, 9)
        for index in range(5):
            db.session.add(DailyReviewSlot(review_date=day, slot=index + 1, clip_id=clips[index].id))
        db.session.commit()
        assert db.session.query(DailyReviewSlot).filter_by(review_date=day).count() == 5

        with pytest.raises(IntegrityError):
            db.session.add(DailyReviewSlot(review_date=day, slot=1, clip_id=clips[5].id))
            db.session.commit()
        db.session.rollback()

        with pytest.raises(IntegrityError):
            db.session.add(DailyReviewSlot(review_date=day, slot=6, clip_id=clips[5].id))
            db.session.commit()
        db.session.rollback()

        with pytest.raises(IntegrityError):
            db.session.add(DailyReviewSlot(review_date=day, slot=1, clip_id=clips[0].id))
            db.session.commit()
        db.session.rollback()

        db.session.add(DailyReviewSlot(review_date=date(2026, 11, 10), slot=1, clip_id=clips[5].id))
        db.session.commit()
        assert db.session.query(DailyReviewSlot).count() == 6
