"""Private in-browser preview of locally rendered, authorized clips."""
from pathlib import Path

from flask import Blueprint, current_app, jsonify, send_file

from ..models import db, Clip, MediaSource
from ..security import admin_only
from ..services.rights import assess_rights

previews_bp = Blueprint("previews", __name__)


@previews_bp.get("/clips/<int:clip_id>/preview")
@admin_only
def preview_clip(clip_id):
    clip = db.session.get(Clip, clip_id)
    if clip is None or clip.editorial_status != "ready" or not clip.output_path:
        return jsonify(error="Clip no disponible"), 404
    source = db.session.get(MediaSource, clip.source_id)
    if source is None or not assess_rights(
        source.rights_status, source.permission_evidence
    ).allowed:
        return jsonify(error="No se pueden previsualizar archivos sin autorización"), 403

    clips_directory = (Path(current_app.config["MEDIA_ROOT"]) / "clips").resolve()
    video = Path(clip.output_path).resolve()
    if video.parent != clips_directory or not video.is_file() or video.suffix.lower() != ".mp4":
        return jsonify(error="Archivo no disponible para previsualización"), 404

    # conditional=True supports HTTP range requests for HTML5's <video> player.
    response = send_file(
        video, mimetype="video/mp4", conditional=True,
        as_attachment=False, download_name=f"autoclip-{clip.id}.mp4"
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
