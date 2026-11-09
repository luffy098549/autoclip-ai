"""Transcribe authorized media, discover candidates, render and optionally burn captions."""
import argparse
from app import create_app
from app.models import db, Clip
from app.services.analyzer import analyze_source
from app.services.clip_processor import process_clip


def main():
    parser = argparse.ArgumentParser(description="AutoClip local end-to-end processing")
    parser.add_argument("source_id", type=int, help="Previously imported and authorized source ID")
    parser.add_argument("--model", default="small", help="Local faster-whisper model")
    parser.add_argument("--max-clips", type=int, default=5)
    parser.add_argument("--burn-subtitles", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_clips <= 5:
        parser.error("max-clips must be between 1 and 5")
    app = create_app({"AUTO_CAPTION_ENABLED": args.burn_subtitles})
    with app.app_context():
        result = analyze_source(args.source_id, model_size=args.model, max_clips=args.max_clips)
        print("Transcribed segments:", result["transcript_segments"])
        print("Candidates selected:", result["candidate_count"])
        for clip_id in result["clip_ids"]:
            clip = db.session.get(Clip, clip_id)
            if clip.editorial_status == "ready":
                print("Already rendered:", clip_id)
                continue
            try:
                exported = process_clip(clip_id)
                print("Rendered clip:", clip_id, exported.get("captioned_path") or exported["path"])
            except Exception as exc:
                print("Clip", clip_id, "failed:", type(exc).__name__)
        print("Review every exported clip before uploading to a social platform.")


if __name__ == "__main__":
    main()
