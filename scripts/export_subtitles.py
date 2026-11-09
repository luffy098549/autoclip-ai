"""Export subtitle sidecar for a clip: python -m scripts.export_subtitles ID"""
import argparse
from pathlib import Path
from app import create_app
from app.services.subtitle_export import export_clip_srt

parser = argparse.ArgumentParser()
parser.add_argument("clip_id", type=int)
args = parser.parse_args()
app = create_app()
with app.app_context():
    path = Path(app.config["MEDIA_ROOT"]) / "subtitles" / f"clip-{args.clip_id}.srt"
    result = export_clip_srt(args.clip_id, path)
    if not result:
        raise SystemExit("No transcript segments overlap this clip")
    print(result)
