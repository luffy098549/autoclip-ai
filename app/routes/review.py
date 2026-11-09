"""Owner-only daily review candidates backed by the existing clips database.

Read-only: no downloads, scheduling, or social publishing are triggered.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from ..models import Clip, MediaSource
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
