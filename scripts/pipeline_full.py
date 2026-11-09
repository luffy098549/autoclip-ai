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
    if args.source_id <= 0:
        parser.error("source_id must be a positive integer")
    if not 1 <= args.max_clips <= 5:
        parser.error("max-clips must be between 1 and 5")
    app = create_app({"AUTO_CAPTION_ENABLED": args.burn_subtitles})
    with app.app_context():
        result = analyze_source(args.source_id, model_size=args.model, max_clips=args.max_clips)
        print("Transcribed segments:", result["transcript_segments"])
        print("Candidates selected:", result["candidate_count"])
        rendered = 0
        failed = 0
        already_ready = 0
        for clip_id in result["clip_ids"]:
            try:
                try:
                    clip = db.session.get(Clip, clip_id)
                except Exception:
                    # Reset a failed SQLAlchemy transaction before the next clip.
                    db.session.rollback()
                    raise
                if clip is None:
                    failed += 1
                    print("Clip", clip_id, "failed: not found")
                    continue
                if clip.editorial_status == "ready":
                    already_ready += 1
                    print("Already rendered:", clip_id)
                    continue
                exported = process_clip(clip_id)
                rendered += 1
                print("Rendered clip:", clip_id, exported.get("captioned_path") or exported["path"])
            except Exception as exc:
                failed += 1
                print("Clip", clip_id, "failed:", type(exc).__name__)
        print(f"Pipeline summary: rendered={rendered}, already_ready={already_ready}, failed={failed}")
        print("Review every exported clip before uploading to a social platform.")
        if failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
