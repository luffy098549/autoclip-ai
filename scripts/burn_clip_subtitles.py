"""Create a captioned MP4 for an existing, authorized finished clip."""
import argparse
from pathlib import Path
from app import create_app
from app.models import db, Clip, MediaSource
from app.services.caption_burn import burn_subtitles
from app.services.rights import assess_rights

parser = argparse.ArgumentParser()
parser.add_argument("clip_id", type=int)
args = parser.parse_args()
app = create_app()
with app.app_context():
    clip = db.session.get(Clip, args.clip_id)
    if not clip or clip.editorial_status != "ready" or not clip.output_path:
        raise SystemExit("Clip must exist and be ready")
    source = db.session.get(MediaSource, clip.source_id)
    if not source or not assess_rights(source.rights_status, source.permission_evidence).allowed:
        raise SystemExit("Rights are not verified")
    video = Path(clip.output_path).resolve()
    allowed = (Path(app.config["MEDIA_ROOT"]) / "clips").resolve()
    if video.parent != allowed:
        raise SystemExit("Clip path outside allowed directory")
    subtitle = Path(app.config["MEDIA_ROOT"]) / "subtitles" / f"clip-{clip.id}.srt"
    target = allowed / f"clip-{clip.id}-captioned.mp4"
    info = burn_subtitles(video, subtitle, target)
    clip.output_path = str(target)
    db.session.commit()
    print(f"Subtitled MP4 created: {target} ({info['duration']} seconds)")
