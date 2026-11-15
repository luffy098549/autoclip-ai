"""Owner-only daily review candidates backed by the existing clips database.

Read-only: no downloads, scheduling, or social publishing are triggered.
"""
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.orm import joinedload

from ..models import db, Clip, MediaSource, Publication
from ..security import admin_only
from ..services.rights import assess_rights
from ..intelligence.daily_selection import select_daily_clips

review_bp = Blueprint("review", __name__)


@review_bp.get("/review/daily")
@admin_only
def daily_review():
    """Return the best ready, scored, authorized clips for manual review."""
    try:
        target = int(request.args.get("limit", "5"))
    except (TypeError, ValueError):
        return jsonify(error="limit debe ser un número entero"), 400
    if not 1 <= target <= 20:
        return jsonify(error="limit debe estar entre 1 y 20"), 400

    # Limit query size while still allowing multiple candidates per source.
    candidates = (
        Clip.query.filter(Clip.editorial_status == "ready", Clip.score.isnot(None))
        .order_by(Clip.score.desc(), Clip.id.asc())
        .limit(1000).all()
    )
    source_ids = {clip.source_id for clip in candidates}
    sources = {
        source.id: source
        for source in MediaSource.query.filter(MediaSource.id.in_(source_ids)).all()
    } if source_ids else {}
    eligible = [
        clip for clip in candidates
        if clip.output_path
        and (source := sources.get(clip.source_id)) is not None
        and assess_rights(source.rights_status, source.permission_evidence).allowed
    ]
    selected = select_daily_clips(eligible, target=target)
    return jsonify(
        target=target, count=len(selected), publishing_enabled=False,
        note="Cola de revisión manual; no publica ni descarga medios automáticamente.",
        items=[{
            "clip_id": clip.clip_id, "source_id": clip.source_id,
            "start": clip.start_seconds, "end": clip.end_seconds,
            "score": clip.score,
            "preview_url": f"/api/clips/{clip.clip_id}/preview",
            "download_url": f"/api/clips/{clip.clip_id}/download",
        } for clip in selected],
    )


@review_bp.get("/review/youtube-preflight/<int:clip_id>")
@admin_only
def youtube_preflight(clip_id):
    """Read-only checks before an owner-approved private YouTube upload."""
    clip = db.session.get(Clip, clip_id)
    if clip is None:
        return jsonify(error="Clip no encontrado", ready=False), 404
    source = db.session.get(MediaSource, clip.source_id)
    rights = (assess_rights(source.rights_status, source.permission_evidence).allowed
              if source is not None else False)
    root = (Path(current_app.config["MEDIA_ROOT"]) / "clips").resolve()
    video = Path(clip.output_path).resolve() if clip.output_path else None
    upload_record = (Publication.query.filter_by(clip_id=clip_id, platform="youtube")
                     .filter(Publication.state.in_(("publishing", "published", "upload_uncertain")))
                     .order_by(Publication.id.desc()).first())
    checks = {
        "no_existing_upload_attempt": upload_record is None,
        "editorial_ready": clip.editorial_status == "ready",
        "rights_evidence_present": rights,
        "mp4_in_private_clips_directory": bool(video and video.parent == root and video.is_file() and video.suffix.lower() == ".mp4"),
        "youtube_oauth_token_present": (Path(current_app.config["MEDIA_ROOT"]) / "private" / "youtube-token.json").is_file(),
        "publishing_disabled": not current_app.config.get("PUBLISHING_ENABLED", False),
    }
    return jsonify(clip_id=clip_id, ready=all(checks.values()), checks=checks,
                   privacy="private", uploaded=bool(upload_record and upload_record.state == "published"),
                   upload_state=upload_record.state if upload_record else None,
                   note="Solo comprobación local. No envía datos ni videos a YouTube.")
