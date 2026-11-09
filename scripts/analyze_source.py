"""AI transcription + heuristic highlight discovery, for licensed local videos."""
import argparse
from pathlib import Path
from app import create_app
from app.models import db, MediaSource, Clip, TranscriptSegment
from app.services.rights import assess_rights
from app.services.transcription import transcribe_file
from app.intelligence.highlights import score_candidates

parser = argparse.ArgumentParser()
parser.add_argument("source_id", type=int)
parser.add_argument("--model", default="small")
parser.add_argument("--max-clips", type=int, default=5)
parser.add_argument("--render", action="store_true", help="Render shortlisted clips locally with FFmpeg")
args = parser.parse_args()
if not 1 <= args.max_clips <= 5:
    parser.error("--max-clips must be from 1 to 5")

app = create_app()
with app.app_context():
    source = db.session.get(MediaSource, args.source_id)
    if not source:
        raise SystemExit("Source was not found")
    if not assess_rights(source.rights_status, source.permission_evidence).allowed:
        raise SystemExit("Source rights are not confirmed")
    if not Path(source.source_uri).is_file():
        raise SystemExit("Source video file is missing")

    transcript = TranscriptSegment.query.filter_by(source_id=source.id).order_by(
        TranscriptSegment.start_seconds).all()
    if not transcript:
        data = transcribe_file(source.source_uri, model_size=args.model)
        for s in data["segments"]:
            db.session.add(TranscriptSegment(
                source_id=source.id, start_seconds=s["start"],
                end_seconds=s["end"], text=s["text"], language=data["language"]))
        db.session.commit()
        transcript = TranscriptSegment.query.filter_by(source_id=source.id).order_by(
            TranscriptSegment.start_seconds).all()

    candidates = score_candidates(
        [{"start": x.start_seconds, "end": x.end_seconds, "text": x.text} for x in transcript],
        max_clips=args.max_clips,
    )
    ids = []
    for cand in candidates:
        # Avoid duplicate inserts when analyzing the same source more than once.
        existing = Clip.query.filter_by(source_id=source.id, start_seconds=cand.start,
                                        end_seconds=cand.end).first()
        if existing:
            ids.append(existing.id)
            continue
        clip = Clip(source_id=source.id, start_seconds=cand.start,
                    end_seconds=cand.end, score=cand.score,
                    editorial_status="awaiting_worker")
        db.session.add(clip)
        db.session.flush()
        ids.append(clip.id)
    db.session.commit()
    print(f"Candidates: {len(ids)} | Clip IDs: {ids}")
    if args.render:
        from app.services.clip_processor import process_clip
        for clip_id in ids:
            clip = db.session.get(Clip, clip_id)
            if clip.editorial_status == "ready":
                continue
            print(f"Rendering clip {clip_id}...")
            process_clip(clip_id)
