"""Worker-safe clip processing. Requires prior source authorization."""
from pathlib import Path
from flask import current_app
from ..models import db, Clip, MediaSource
from .rights import assess_rights
from ..pipeline import create_local_clip


def process_clip(clip_id: int):
    clip = db.session.get(Clip, clip_id)
    if clip is None:
        raise ValueError("Clip no encontrado")
    source = db.session.get(MediaSource, clip.source_id)
    if source is None or not assess_rights(source.rights_status, source.permission_evidence).allowed:
        clip.editorial_status = "rejected"
        db.session.commit()
        raise PermissionError("La fuente no tiene autorización válida")
    clip.editorial_status = "processing"
    db.session.commit()
    target = Path(current_app.config["MEDIA_ROOT"]) / "clips" / f"clip-{clip.id}.mp4"
    try:
        info = create_local_clip(source.source_uri, target, start=clip.start_seconds,
                                 end=clip.end_seconds, authorized=True)
        from .subtitle_export import export_clip_srt
        subtitles = Path(current_app.config["MEDIA_ROOT"]) / "subtitles" / f"clip-{clip.id}.srt"
        subtitle_path = export_clip_srt(clip.id, subtitles)
        clip.output_path = info["path"]
        if subtitle_path and current_app.config.get("AUTO_CAPTION_ENABLED"):
            from .caption_burn import burn_subtitles
            captioned = target.with_name(f"clip-{clip.id}-captioned.mp4")
            burn_subtitles(info["path"], subtitle_path, captioned)
            clip.output_path = str(captioned)
            info["captioned_path"] = str(captioned)
        clip.editorial_status = "ready"
        db.session.commit()
        return info
    except Exception:
        db.session.rollback()
        clip = db.session.get(Clip, clip_id)
        clip.editorial_status = "failed"
        db.session.commit()
        raise
