"""Worker-safe clip processing. Requires prior source authorization."""
from pathlib import Path
from flask import current_app
from sqlalchemy import update
from ..models import db, Clip, MediaSource
from .rights import assess_rights
from ..pipeline import create_local_clip


def process_clip(clip_id: int):
    clip = db.session.get(Clip, clip_id)
    if clip is None:
        raise ValueError("Clip no encontrado")
    source = db.session.get(MediaSource, clip.source_id)
    if source is None or not assess_rights(source.rights_status, source.permission_evidence).allowed:
        # Do not downgrade reviewed/published clips if rights are later revoked.
        db.session.execute(
            update(Clip)
            .where(Clip.id == clip_id, Clip.editorial_status.in_(("draft", "failed", "awaiting_worker")))
            .values(editorial_status="rejected")
            .execution_options(synchronize_session="fetch")
        )
        db.session.commit()
        raise PermissionError("La fuente no tiene autorización válida")
    # Atomic compare-and-set prevents competing workers from rendering the same clip.
    claimed = db.session.execute(
        update(Clip)
        .where(Clip.id == clip_id, Clip.editorial_status.in_(("draft", "failed", "awaiting_worker")))
        .values(editorial_status="processing")
        .execution_options(synchronize_session="fetch")
    )
    db.session.commit()
    if claimed.rowcount != 1:
        raise RuntimeError("Clip is already processing or not eligible for rendering")
    target = Path(current_app.config["MEDIA_ROOT"]) / "clips" / f"clip-{clip.id}.mp4"
    # Only remove artifacts created by this attempt. Never delete a pre-existing export.
    created_artifacts = []
    try:
        # Register the output before invoking FFmpeg: it can leave a partial file
        # even when it raises. Never take ownership of an existing export.
        if target.exists():
            raise FileExistsError(f"Clip export already exists: {target.name}")
        created_artifacts.append(target)
        info = create_local_clip(source.source_uri, target, start=clip.start_seconds,
                                 end=clip.end_seconds, authorized=True)
        from .subtitle_export import export_clip_srt
        subtitles = Path(current_app.config["MEDIA_ROOT"]) / "subtitles" / f"clip-{clip.id}.srt"
        # Register before writing: a failed exporter may leave a partial sidecar.
        # Only own newly created paths, never a previous reviewed export.
        if not subtitles.exists():
            created_artifacts.append(subtitles)
        subtitle_path = export_clip_srt(clip.id, subtitles)
        clip.output_path = info["path"]
        if subtitle_path and current_app.config.get("AUTO_CAPTION_ENABLED"):
            from .caption_burn import burn_subtitles
            captioned = target.with_name(f"clip-{clip.id}-captioned.mp4")
            # Caption rendering can create a partial output before raising.
            # Register only new files before invoking FFmpeg, and never overwrite
            # an existing captioned export from a previous attempt.
            if captioned.exists():
                raise FileExistsError(f"Captioned export already exists: {captioned.name}")
            created_artifacts.append(captioned)
            burn_subtitles(info["path"], subtitle_path, captioned)
            clip.output_path = str(captioned)
            info["captioned_path"] = str(captioned)
        clip.editorial_status = "ready"
        db.session.commit()
        return info
    except Exception:
        for artifact in reversed(created_artifacts):
            artifact.unlink(missing_ok=True)
        db.session.rollback()
        clip = db.session.get(Clip, clip_id)
        clip.editorial_status = "failed"
        db.session.commit()
        raise
