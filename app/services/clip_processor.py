"""Worker-safe clip processing. Requires prior source authorization."""
from pathlib import Path
from flask import current_app
from ..models import db, Clip, MediaSource
from .rights import assess_rights
from ..pipeline import create_local_clip


class SourceAuthorizationRevoked(PermissionError):
    """Source rights were revoked; this failure must never be retried."""


class ClipNotEligibleError(RuntimeError):
    """Another worker claimed the clip, or its status forbids rendering."""


def process_clip(clip_id: int):
    clip = db.session.get(Clip, clip_id)
    if clip is None:
        raise ValueError("Clip no encontrado")
    # Resolve output paths before claiming the record. A missing or invalid
    # MEDIA_ROOT must not strand the clip in processing status.
    target = Path(current_app.config["MEDIA_ROOT"]) / "clips" / f"clip-{clip.id}.mp4"
    subtitles = Path(current_app.config["MEDIA_ROOT"]) / "subtitles" / f"clip-{clip.id}.srt"
    captioned = target.with_name(f"clip-{clip.id}-captioned.mp4")
    # Claim before touching editorial state: a stale worker must not reject a
    # clip that another worker is already processing or has completed.
    # Claim atomically to prevent concurrent workers overwriting one output.
    claimed = db.session.query(Clip).filter(
        Clip.id == clip_id,
        Clip.editorial_status.in_(("draft", "failed", "awaiting_worker", "queued")),
    ).update({Clip.editorial_status: "processing"}, synchronize_session=False)
    db.session.commit()
    if claimed != 1:
        raise ClipNotEligibleError("Clip already processing or not eligible for rendering")
    db.session.refresh(clip)
    try:
        # Rights lookup and evaluation must be inside the failure handler.
        # A database error here must not leave a clip stuck in "processing".
        source = db.session.get(MediaSource, clip.source_id)
        if source is None or not assess_rights(
            source.rights_status, source.permission_evidence
        ).allowed:
            raise SourceAuthorizationRevoked("La fuente no tiene autorización válida")
        # A retry must not reuse artifacts left by an earlier attempt. In
        # particular, a successful render without captions must not expose an
        # obsolete SRT or captioned MP4 from a previous run.
        for artifact in (target, captioned, subtitles):
            artifact.unlink(missing_ok=True)
        info = create_local_clip(source.source_uri, target, start=clip.start_seconds,
                                 end=clip.end_seconds, authorized=True)
        from .subtitle_export import export_clip_srt
        subtitle_path = export_clip_srt(clip.id, subtitles)
        clip.output_path = info["path"]
        if subtitle_path and current_app.config.get("AUTO_CAPTION_ENABLED"):
            from .caption_burn import burn_subtitles
            burn_subtitles(info["path"], subtitle_path, captioned)
            clip.output_path = str(captioned)
            info["captioned_path"] = str(captioned)
            # Return the same playable artifact that the database exposes.
            # Callers must not accidentally preview the uncaptioned render.
            info["path"] = str(captioned)
        # Authorization can be revoked while FFmpeg is running. Reload the
        # source from the database before exposing a completed render.
        db.session.expire(source)
        if not assess_rights(source.rights_status, source.permission_evidence).allowed:
            raise SourceAuthorizationRevoked("Source authorization revoked during rendering")
        clip.editorial_status = "ready"
        db.session.commit()
        return info
    except Exception as error:
        # A revoked or failed render must not leave generated media accessible
        # on disk. Only remove paths derived from this clip id, never paths
        # returned by an encoder or supplied by an external source.
        for artifact in (target, captioned, subtitles):
            try:
                artifact.unlink(missing_ok=True)
            except OSError:
                current_app.logger.warning("Could not remove failed clip artifact: %s", artifact.name)
        db.session.rollback()
        clip = db.session.get(Clip, clip_id)
        # A failed retry must never retain a previously rendered download path.
        clip.output_path = None
        # Revocation is an authorization decision, not an encoder failure.
        # Keep the clip rejected so recovery jobs cannot retry it as a
        # transient failure without a fresh rights review.
        clip.editorial_status = "rejected" if isinstance(
            error, SourceAuthorizationRevoked
        ) else "failed"
        db.session.commit()
        raise
