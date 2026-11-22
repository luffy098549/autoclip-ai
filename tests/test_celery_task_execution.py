"""Exercise Celery task dispatch synchronously without an external broker."""
from types import SimpleNamespace

from app.tasks import celery_app, heartbeat, render_clip_task


def test_celery_heartbeat_eager_execution():
    old = celery_app.conf.task_always_eager
    try:
        celery_app.conf.task_always_eager = True
        result = heartbeat.delay()
        assert result.successful()
        assert result.get()["status"] == "alive"
    finally:
        celery_app.conf.task_always_eager = old


def test_celery_render_task_enters_flask_context(monkeypatch):
    import app
    import app.services.clip_processor as processor
    import app.services.daily_review as daily_review
    from app.models import Clip, MediaSource, db

    flask_app = app.create_app({
        "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "celery-ci-only",
    })
    seen = []
    reserved = []

    def fake_get(model, identifier):
        from flask import current_app
        assert current_app == flask_app
        if model is Clip and identifier == 42:
            return SimpleNamespace(editorial_status="draft", source_id=7)
        if model is MediaSource and identifier == 7:
            return SimpleNamespace(rights_status="owned", permission_evidence="original test footage")
        return None

    def fake_reserve(clip_id):
        reserved.append(clip_id)
        return 1

    def fake_process(clip_id):
        from flask import current_app
        assert current_app == flask_app
        seen.append(clip_id)
        return {"clip_id": clip_id, "status": "ready"}

    monkeypatch.setattr(app, "create_app", lambda: flask_app)
    monkeypatch.setattr(db.session, "get", fake_get)
    monkeypatch.setattr(daily_review, "reserve_review_slot", fake_reserve)
    monkeypatch.setattr(processor, "process_clip", fake_process)
    old = celery_app.conf.task_always_eager
    try:
        celery_app.conf.task_always_eager = True
        result = render_clip_task.delay(42)
        assert result.successful()
        assert result.get() == {"clip_id": 42, "status": "ready"}
        assert reserved == [42]
        assert seen == [42]
    finally:
        celery_app.conf.task_always_eager = old
