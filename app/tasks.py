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


@celery_app.task(name="autoclip.analyze_source_task")
def analyze_source_task(source_id: int):
    from . import create_app
    from .services.analyzer import analyze_source
    app = create_app()
    with app.app_context():
        result = analyze_source(source_id)
        if app.config.get("AUTO_RENDER_ENABLED"):
            from .models import db, Clip
            from .services.clip_processor import process_clip
            from .services.daily_review import reserve_review_slot
            from .services.rights import assess_rights
            from .models import MediaSource
            successes = []
            failures = []
            for clip_id in result["clip_ids"]:
                clip = db.session.get(Clip, clip_id)
                if clip and clip.editorial_status == "ready":
                    successes.append(clip_id)
                    continue
                try:
                    if not clip or clip.editorial_status in {"rejected", "processing", "approved", "published"}:
                        continue
                    source = db.session.get(MediaSource, clip.source_id)
                    if source is None or not assess_rights(source.rights_status, source.permission_evidence).allowed:
                        failures.append(clip_id)
                        continue
                    if reserve_review_slot(clip_id) is None:
                        result.setdefault("deferred_clip_ids", []).append(clip_id)
                        continue
                    process_clip(clip_id)
                    successes.append(clip_id)
                except Exception:
                    # process_clip persists a failed state. Do not abort other candidates.
                    failures.append(clip_id)
            result["rendered_clip_ids"] = successes
            result["failed_clip_ids"] = failures
        return result


@celery_app.task(name="autoclip.youtube_metadata_task")
def youtube_metadata_task(streamer_id: int):
    import os
    from . import create_app
    from .services.competitor_sync import sync_youtube_channel
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY missing")
    app = create_app()
    with app.app_context():
        return sync_youtube_channel(streamer_id, key)


@celery_app.task(name="autoclip.daily_auto_plan_task")
def daily_auto_plan_task():
    """Idempotent local scheduling; publishing remains a separate, disabled step."""
    from . import create_app
    from .services.auto_planner import build_daily_plan
    app = create_app()
    with app.app_context():
        if not app.config.get("AUTO_PLANNING_ENABLED") or app.config.get("READ_ONLY_DEPLOYMENT"):
            return {"skipped": True, "reason": "AUTO_PLANNING_ENABLED is off"}
        from .services.score_backfill import score_existing_clips
        scores = score_existing_clips(limit=100)
        plan = build_daily_plan(platforms=("youtube", "tiktok", "instagram"), dry_run=False)
        plan["score_backfill"] = scores
        return plan


@celery_app.task(name="autoclip.dispatch_due_task")
def dispatch_due_task():
    from . import create_app
    from .services.auto_dispatch import dispatch_due
    app = create_app()
    with app.app_context():
        return dispatch_due()


# Celery Beat evaluates the planner once a day in New York time.
# It creates local plans only and never uploads to social networks.
from celery.schedules import crontab
celery_app.conf.beat_schedule = {
    "daily-clip-planning": {
        "task": "autoclip.daily_auto_plan_task",
        "schedule": crontab(hour=9, minute=0),
    },
    "dispatch-due-private-youtube": {
        "task": "autoclip.dispatch_due_task",
        "schedule": 300.0,
    },
}
