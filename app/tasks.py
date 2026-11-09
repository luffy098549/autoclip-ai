import os
from celery import Celery

celery_app = Celery(
    "autoclip",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)
celery_app.conf.timezone = "America/New_York"


@celery_app.task
def heartbeat():
    return {"service": "autoclip", "status": "alive"}


@celery_app.task(name="autoclip.render_clip_task")
def render_clip_task(clip_id: int):
    from . import create_app
    from .services.clip_processor import process_clip
    app = create_app()
    with app.app_context():
        return process_clip(clip_id)
