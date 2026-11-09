"""Manual YouTube upload with rights gates, local locking and non-duplicating state."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from app import create_app
from app.models import db, Clip, MediaSource, Publication
from app.publishers.youtube import upload_short
from app.scheduler import can_schedule
from app.services.rights import assess_rights


def publish_clip(clip_id, title, description, token_file, privacy, made_for_kids):
    app = create_app()
    with app.app_context():
        now = datetime.now(timezone.utc)
        if db.engine.dialect.name == "postgresql":
            db.session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": 100091})
        clip = db.session.get(Clip, clip_id)
        if not clip or clip.editorial_status != "ready" or not clip.output_path:
            raise ValueError("Clip must be rendered and ready")
        source = db.session.get(MediaSource, clip.source_id)
        if not source or not assess_rights(
            source.rights_status, source.permission_evidence
        ).allowed:
            raise PermissionError("Source editing and publishing rights are unverified")
        path = Path(clip.output_path).resolve()
        expected_dir = (Path(app.config["MEDIA_ROOT"]) / "clips").resolve()
        if path.parent != expected_dir or not path.is_file():
            raise ValueError("Source clip must exist under the private clips folder")
        previous = Publication.query.filter(
            Publication.clip_id == clip_id, Publication.platform == "youtube",
            Publication.state.in_(("planned", "uploading", "needs_review", "published")),
        ).first()
        if previous:
            raise RuntimeError(
                "Clip already has a YouTube plan or upload record; reconcile or cancel it"
            )
        relevant = Publication.query.filter(
            Publication.platform == "youtube",
            Publication.state.in_(("planned", "scheduled", "uploading", "published",
                                   "needs_review")),
        ).all()
        times = []
        for item in relevant:
            moment = item.published_at if item.state == "published" and item.published_at else item.scheduled_at
            times.append(moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment)
        if not can_schedule(now, times):
            raise RuntimeError("YouTube limit exceeded: 120 minutes and five per day")
        record = Publication(
            clip_id=clip_id, platform="youtube", scheduled_at=now,
            state="uploading", idempotency_key="yt-cli-" + uuid4().hex,
        )
        db.session.add(record)
        db.session.commit()
        try:
            external_id = upload_short(
                path, title, description,
                token_path=token_file,
                privacy_status=privacy,
                made_for_kids=made_for_kids,
            )
        except Exception:
            db.session.rollback()
            record = db.session.get(Publication, record.id)
            record.state = "needs_review"
            db.session.commit()
            raise RuntimeError(
                "Upload failed or its final status is unknown. Inspect YouTube Studio "
                "before attempting another upload; the record is locked for review."
            ) from None
        record = db.session.get(Publication, record.id)
        record.external_id = external_id
        record.published_at = datetime.now(timezone.utc)
        record.state = "published"
        db.session.commit()
        return external_id


def main():
    parser = argparse.ArgumentParser(description="Publish your reviewed clip to your own YouTube channel")
    parser.add_argument("clip_id", type=int)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--token", default="storage/private/youtube-token.json")
    parser.add_argument("--privacy", choices=("private", "unlisted", "public"), default="private")
    parser.add_argument("--made-for-kids", choices=("yes", "no"), required=True)
    parser.add_argument("--confirm-reviewed-and-authorized", action="store_true", required=True)
    args = parser.parse_args()
    if not args.confirm_reviewed_and_authorized:
        parser.error("Review clip quality, creator permissions and platform policy first")
    video_id = publish_clip(args.clip_id, args.title, args.description, args.token,
                            args.privacy, args.made_for_kids == "yes")
    print("YouTube upload completed with ID:", video_id)


if __name__ == "__main__":
    main()
