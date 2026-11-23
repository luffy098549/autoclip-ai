"""Manual render batches share the persistent review budget with analysis."""
from app import create_app
from app.models import Clip, MediaSource, db
from app.services.daily_review import reserve_review_slot
from app.tasks import render_clip_batch_task


def test_batch_defers_when_daily_review_slots_are_full(monkeypatch, tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        try:
            source = MediaSource(
                source_uri=str(tmp_path / "owned.mp4"),
                rights_status="owned",
                permission_evidence="original recording owned by operator",
            )
            db.session.add(source)
            db.session.flush()
            clips = [
                Clip(source_id=source.id, start_seconds=i, end_seconds=i + 1,
                     editorial_status="awaiting_worker")
                for i in range(6)
            ]
            db.session.add_all(clips)
            db.session.commit()
            for clip in clips[:5]:
                assert reserve_review_slot(clip.id) is not None

            monkeypatch.setattr("app.create_app", lambda: app)
            def must_not_render(_clip_id):
                raise AssertionError("review budget bypassed")
            monkeypatch.setattr(
                "app.services.clip_processor.process_clip", must_not_render
            )
            result = render_clip_batch_task.run([clips[5].id])
            assert result["deferred_clip_ids"] == [clips[5].id]
            assert result["rendered_clip_ids"] == []
            assert result["failed_clip_ids"] == []
            db.session.expire_all()
            assert db.session.get(Clip, clips[5].id).editorial_status == "awaiting_worker"
        finally:
            db.session.remove()
            db.drop_all()


def test_batch_reserves_slot_before_rendering(monkeypatch, tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "MEDIA_ROOT": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        try:
            source = MediaSource(
                source_uri=str(tmp_path / "owned.mp4"),
                rights_status="owned",
                permission_evidence="original recording owned by operator",
            )
            db.session.add(source)
            db.session.flush()
            clip = Clip(source_id=source.id, start_seconds=0, end_seconds=1,
                        editorial_status="awaiting_worker")
            db.session.add(clip)
            db.session.commit()
            monkeypatch.setattr("app.create_app", lambda: app)
            def verify_reserved(clip_id):
                assert clip_id == clip.id
                assert reserve_review_slot(clip_id) is not None
            monkeypatch.setattr(
                "app.services.clip_processor.process_clip", verify_reserved
            )
            result = render_clip_batch_task.run([clip.id])
            assert result["rendered_clip_ids"] == [clip.id]
            assert result["deferred_clip_ids"] == []
        finally:
            db.session.remove()
            db.drop_all()
