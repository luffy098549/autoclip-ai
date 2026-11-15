"""Deterministic daily planning for ready, scored clips.

Creates local publication plans only; never calls a platform API.
"""
from datetime import datetime, timedelta, timezone, time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from ..models import db, Clip, MediaSource, Publication
from ..scheduler import TIMEZONE, PLATFORMS, can_schedule
from ..services.rights import assess_rights
from ..intelligence.daily_selection import select_daily_clips

ACTIVE = ("planned", "scheduled", "publishing", "published", "upload_uncertain")


def build_daily_plan(*, date=None, platforms=("youtube",), dry_run=True, limit=5):
    if not 1 <= limit <= 5:
        raise ValueError("limit must be between 1 and 5")
    if not platforms or any(p not in PLATFORMS for p in platforms):
        raise ValueError("Unsupported platform")
    today = datetime.now(TIMEZONE).date()
    date = date or today
    if date < today:
        raise ValueError("Cannot plan past dates")
    if db.engine.dialect.name == "postgresql" and not dry_run:
        db.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 700104})
    candidates = (Clip.query.filter(Clip.editorial_status == "ready", Clip.score.isnot(None))
                  .order_by(Clip.score.desc(), Clip.id.asc()).limit(1000).all())
    sources = {s.id: s for s in MediaSource.query.filter(
        MediaSource.id.in_({c.source_id for c in candidates})).all()} if candidates else {}
    eligible = [c for c in candidates if c.output_path
                and Path(c.output_path).is_file()
                and (s := sources.get(c.source_id)) is not None
                and assess_rights(s.rights_status, s.permission_evidence).allowed]
    selected = select_daily_clips(eligible, target=min(20, max(limit * 4, 5)))
    existing = Publication.query.filter(Publication.platform.in_(platforms)).all()
    reserved = {(p.clip_id, p.platform) for p in existing if p.state in ACTIVE}
    # Never plan a clip already sent to this platform, even in a prior day.
    # Five windows spaced by 2h, beginning at 10:00 New York time.
    windows = [datetime.combine(date, time(10 + 2 * i), tzinfo=TIMEZONE)
               for i in range(limit)]
    now = datetime.now(timezone.utc)
    proposed = []
    for platform in platforms:
        times = [(p.scheduled_at.replace(tzinfo=timezone.utc)
                  if p.scheduled_at.tzinfo is None else p.scheduled_at.astimezone(timezone.utc))
                 for p in existing if p.platform == platform and p.state in ACTIVE]
        for window in windows:
            moment = window.astimezone(timezone.utc)
            if moment <= now or not can_schedule(moment, times):
                continue
            candidate = next((c for c in selected if (c.clip_id, platform) not in reserved
                              and not any(x["clip_id"] == c.clip_id for x in proposed
                                          if x["platform"] == platform)), None)
            if candidate is None:
                break
            proposed.append({"clip_id": candidate.clip_id, "platform": platform,
                             "scheduled_at": moment.isoformat(), "score": candidate.score})
            times.append(moment)
            reserved.add((candidate.clip_id, platform))
            if not dry_run:
                db.session.add(Publication(clip_id=candidate.clip_id, platform=platform,
                                           scheduled_at=moment, state="planned",
                                           idempotency_key=uuid4().hex))
    if not dry_run:
        db.session.commit()
    return {"date": date.isoformat(), "dry_run": dry_run, "created": len(proposed),
            "items": proposed, "note": "Local plans only; no videos uploaded"}
