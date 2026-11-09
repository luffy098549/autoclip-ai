"""Manually process a queued clip: python -m scripts.process_clip CLIP_ID."""
import argparse
from app import create_app
from app.services.clip_processor import process_clip

parser = argparse.ArgumentParser()
parser.add_argument("clip_id", type=int)
args = parser.parse_args()
app = create_app()
with app.app_context():
    result = process_clip(args.clip_id)
    print(result["path"])
