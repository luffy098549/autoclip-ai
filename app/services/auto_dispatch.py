"""Opt-in, private-only scheduled YouTube dispatcher.

Claim each row before calling YouTube; unknown results never auto-retry.
TikTok and Instagram remain planned until their official integrations exist.
"""
from datetime import datetime, timezone
from pathlib import Path

from ..models import db, Publication, Clip, MediaSource
from ..services.rights import assess_rights
from ..quality import validate_render


def dispatch_due(*, now=None, max_items=5):
    from flask import current_app
    if not current_app.config.get("AUTO_PUBLISH_YOUTUBE_PRIVATE", False):
        return {"skipped": True, "reason": "AUTO_PUBLISH_YOUTUBE_PRIVATE disabled"}
    if current_app.config.get("READ_ONLY_DEPLOYMENT"):
        return {"skipped": True, "reason": "read-only deployment"}
    now = now or datetime.now(timezone.utc)
    if not 1 <= max_items <= 5:
        raise ValueError("max_items must be 1..5")
    results = []
    # PostgreSQL row-level locks prevent two workers from claiming the same item.
    query = (Publication.query.filter(Publication.platform == "youtube",
                                      Publication.state == "planned",
                                      Publication.scheduled_at <= now)
             .order_by(Publication.scheduled_at, Publication.id))
    if db.engine.dialect.name == "postgresql":
        query = query.with_for_update(skip_locked=True)
    # Claim one row at a time; commit the claim before network I/O.
    for _ in range(max_items):
        item = query.first()
        if item is None:
            break
        item.state = "publishing"
        db.session.commit()

        clip = db.session.get(Clip, item.clip_id)
        source = db.session.get(MediaSource, clip.source_id) if clip else None
        if not clip or clip.editorial_status != "ready" or not clip.output_path or not source:
            item.state = "blocked"
            db.session.commit()
            results.append({"publication_id": item.id, "state": "blocked"})
            continue
        if not assess_rights(source.rights_status, source.permission_evidence).allowed:
            item.state = "blocked"
            db.session.commit()
            results.append({"publication_id": item.id, "state": "blocked"})
            continue
        root = (Path(current_app.config["MEDIA_ROOT"]) / "clips").resolve()
        video = Path(clip.output_path).resolve()
        if (video.parent != root or video.suffix.lower() != ".mp4" or not video.is_file()):
            item.state = "blocked"
            db.session.commit()
            results.append({"publication_id": item.id, "state": "blocked"})
            continue
        try:
            validate_render(video)
        except Exception:
            item.state = "blocked"
            db.session.commit()
            results.append({"publication_id": item.id, "state": "blocked"})
            continue
        token = Path(current_app.config["MEDIA_ROOT"]) / "private" / "youtube-token.json"
        if not token.is_file():
            item.state = "planned"
            db.session.commit()
            results.append({"publication_id": item.id, "state": "waiting_for_youtube"})
            break
        # Do not send a clip twice even if it has another planned row.
        duplicate = (Publication.query.filter(Publication.clip_id == clip.id,
                                              Publication.platform == "youtube",
                                              Publication.id != item.id,
                                              Publication.state.in_((
                                                  "publishing", "published", "upload_uncertain")))
                     .first())
        if duplicate:
            item.state = "blocked"
            db.session.commit()
            results.append({"publication_id": item.id, "state": "blocked_duplicate"})
            continue
        try:
            from ..publishers.youtube import upload_short
            video_id = upload_short(
                str(video), title=f"AutoClip AI - Clip {clip.id}",
                description="Clip procesado con AutoClip AI.",
                token_path=str(token), privacy_status="private", made_for_kids=False)
        except Exception:
            current_app.logger.exception("Scheduled YouTube upload result unknown")
            item.state = "upload_uncertain"
            db.session.commit()
            results.append({"publication_id": item.id, "state": "upload_uncertain"})
            continue
        item.external_id = video_id
        item.published_at = datetime.now(timezone.utc)
        item.state = "published"
        db.session.commit()
        results.append({"publication_id": item.id, "state": "published",
                        "video_id": video_id})
    return {"processed": len(results), "results": results,
            "privacy": "private", "other_platforms": "not_implemented"}
