"""Daily review reservations persist across independent processing calls."""
from datetime import datetime, timezone

from flask_migrate import upgrade

from app import create_app
from app.models import db, Clip, MediaSource, DailyReviewSlot
from app.services.daily_review import reserve_review_slot


def test_reservations_are_persistent_idempotent_and_limited(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "daily.sqlite"),
        "SECRET_KEY": "test-only",
    })
    with app.app_context():
        upgrade()
        source = MediaSource(source_uri="synthetic-local", rights_status="authorized")
        db.session.add(source)
        db.session.flush()
        clips = [Clip(source_id=source.id, start_seconds=i, end_seconds=i + 1)
                 for i in range(7)]
        db.session.add_all(clips)
        db.session.commit()
        now = datetime(2026, 11, 9, 18, tzinfo=timezone.utc)
        assert [reserve_review_slot(clip.id, now) for clip in clips[:5]] == [1, 2, 3, 4, 5]
        assert reserve_review_slot(clips[0].id, now) == 1
        assert reserve_review_slot(clips[5].id, now) is None
        db.session.expire_all()
        assert db.session.query(DailyReviewSlot).count() == 5
        tomorrow = datetime(2026, 11, 10, 18, tzinfo=timezone.utc)
        assert reserve_review_slot(clips[6].id, tomorrow) == 1
        assert reserve_review_slot(clips[0].id, tomorrow) is None
        assert db.session.query(DailyReviewSlot).count() == 6
