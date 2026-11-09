"""Run analysis locally: python -m scripts.analyze_source SOURCE_ID [--render]"""
import argparse
from app import create_app
from app.models import db, Clip
from app.services.analyzer import analyze_source

parser = argparse.ArgumentParser()
parser.add_argument("source_id", type=int)
parser.add_argument("--model", default="small")
parser.add_argument("--max-clips", type=int, default=5)
parser.add_argument("--render", action="store_true")
args = parser.parse_args()
app = create_app()
with app.app_context():
    result = analyze_source(args.source_id, model_size=args.model,
                            max_clips=args.max_clips)
    print(result)
    if args.render:
        from app.services.clip_processor import process_clip
        for clip_id in result["clip_ids"]:
            clip = db.session.get(Clip, clip_id)
            if clip.editorial_status == "ready":
                continue
            print(f"Rendering clip {clip_id}")
            process_clip(clip_id)
