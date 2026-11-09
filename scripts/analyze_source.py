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
if args.source_id <= 0:
    parser.error("source_id must be a positive integer")
if not 1 <= args.max_clips <= 5:
    parser.error("--max-clips must be between 1 and 5")
app = create_app()
with app.app_context():
    result = analyze_source(args.source_id, model_size=args.model,
                            max_clips=args.max_clips)
    print(result)
    if args.render:
        from app.services.clip_processor import process_clip
        rendered = failed = already_ready = 0
        for clip_id in result["clip_ids"]:
            clip = db.session.get(Clip, clip_id)
            if clip is None:
                failed += 1
                print(f"Clip {clip_id} failed: not found")
                continue
            if clip.editorial_status == "ready":
                already_ready += 1
                continue
            try:
                print(f"Rendering clip {clip_id}")
                process_clip(clip_id)
                rendered += 1
            except Exception as exc:
                failed += 1
                print(f"Clip {clip_id} failed: {type(exc).__name__}")
        print(f"Render summary: rendered={rendered}, already_ready={already_ready}, failed={failed}")
        if failed:
            raise SystemExit(1)
