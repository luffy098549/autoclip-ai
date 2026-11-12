"""Exercise Celery task dispatch synchronously without an external broker."""
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

    flask_app = app.create_app({
        "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "celery-ci-only",
    })
    seen = []

    def fake_process(clip_id):
        from flask import current_app
        assert current_app == flask_app
        seen.append(clip_id)
        return {"clip_id": clip_id, "status": "ready"}

    monkeypatch.setattr(app, "create_app", lambda: flask_app)
    monkeypatch.setattr(processor, "process_clip", fake_process)
    old = celery_app.conf.task_always_eager
    try:
        celery_app.conf.task_always_eager = True
        result = render_clip_task.delay(42)
        assert result.successful()
        assert result.get()["clip_id"] == 42
        assert seen == [42]
    finally:
        celery_app.conf.task_always_eager = old
