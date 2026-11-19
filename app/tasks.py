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
                    if not clip or clip.editorial_status not in {"draft", "failed"}:
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
                    # A failed commit or render can invalidate the session; recover
                    # before looking up the next candidate in this batch.
                    db.session.rollback()
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


@celery_app.task(name="autoclip.render_clip_batch_task")
def render_clip_batch_task(clip_ids):
    """Render up to five existing clip records for manual review; never publish.

    Each clip is processed independently so one failed render cannot prevent
    the remaining authorized clips from being attempted.
    """
    if not isinstance(clip_ids, (list, tuple)) or not 1 <= len(clip_ids) <= 5:
        raise ValueError("Provide between one and five clip IDs")
    if any(type(clip_id) is not int or clip_id <= 0 for clip_id in clip_ids):
        raise ValueError("Clip IDs must be positive integers")
    if len(set(clip_ids)) != len(clip_ids):
        raise ValueError("Duplicate clip IDs")

    from . import create_app
    from .services.clip_processor import process_clip
    from .models import db, Clip, MediaSource
    from .services.rights import assess_rights

    app = create_app()
    completed = []
    failed = []
    skipped = []
    unauthorized = []
    with app.app_context():
        for clip_id in clip_ids:
            try:
                clip = db.session.get(Clip, clip_id)
                # Never overwrite an already approved/published clip, or race
                # another worker currently processing the same record.
                if clip is None or clip.editorial_status not in {"draft", "failed"}:
                    skipped.append(clip_id)
                    continue
                source = db.session.get(MediaSource, clip.source_id)
                if source is None or not assess_rights(
                    source.rights_status, source.permission_evidence
                ).allowed:
                    unauthorized.append(clip_id)
                    continue
                process_clip(clip_id)
            except Exception:
                # A failure in one clip must not poison the SQLAlchemy session
                # used for the remaining independent renders.
                db.session.rollback()
                failed.append(clip_id)
            else:
                completed.append(clip_id)
    return {
        "rendered_clip_ids": completed,
        "failed_clip_ids": failed,
        "skipped_clip_ids": skipped,
        "unauthorized_clip_ids": unauthorized,
    }
