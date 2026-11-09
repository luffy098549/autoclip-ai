from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

class Streamer(db.Model):
    __tablename__ = "streamers"
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False)
    platform = db.Column(db.String(30), nullable=False)
    channel_identifier = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=False, nullable=False)
    __table_args__ = (UniqueConstraint("platform", "channel_identifier"),)

class MediaSource(db.Model):
    __tablename__ = "sources"
    id = db.Column(db.Integer, primary_key=True)
    streamer_id = db.Column(db.Integer, db.ForeignKey("streamers.id"), nullable=True)
    source_uri = db.Column(db.Text, nullable=False)
    rights_status = db.Column(db.String(30), default="unverified", nullable=False)
    permission_evidence = db.Column(db.Text)
    acquired_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Clip(db.Model):
    __tablename__ = "clips"
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"), nullable=False)
    start_seconds = db.Column(db.Float, nullable=False)
    end_seconds = db.Column(db.Float, nullable=False)
    score = db.Column(db.Float)
    output_path = db.Column(db.Text)
    editorial_status = db.Column(db.String(30), default="draft", nullable=False)

class Publication(db.Model):
    __tablename__ = "publications"
    id = db.Column(db.Integer, primary_key=True)
    clip_id = db.Column(db.Integer, db.ForeignKey("clips.id"), nullable=False)
    platform = db.Column(db.String(30), nullable=False)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False)
    published_at = db.Column(db.DateTime(timezone=True))
    external_id = db.Column(db.String(255))
    state = db.Column(db.String(30), default="scheduled", nullable=False)
    idempotency_key = db.Column(db.String(128), unique=True, nullable=False)

class TranscriptSegment(db.Model):
    __tablename__ = "transcript_segments"
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"), nullable=False, index=True)
    start_seconds = db.Column(db.Float, nullable=False)
    end_seconds = db.Column(db.Float, nullable=False)
    text = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), nullable=True)

class PerformanceMetric(db.Model):
    __tablename__ = "performance_metrics"
    id = db.Column(db.Integer, primary_key=True)
    clip_id = db.Column(db.Integer, db.ForeignKey("clips.id"), nullable=False, index=True)
    platform = db.Column(db.String(30), nullable=False)
    views = db.Column(db.BigInteger, default=0, nullable=False)
    likes = db.Column(db.BigInteger, default=0, nullable=False)
    comments = db.Column(db.BigInteger, default=0, nullable=False)
    shares = db.Column(db.BigInteger, default=0, nullable=False)
    avg_watch_seconds = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class CompetitorVideo(db.Model):
    """Public YouTube metadata, not the video file or rights to reuse it."""
    __tablename__ = "competitor_videos"
    id = db.Column(db.Integer, primary_key=True)
    streamer_id = db.Column(db.Integer, db.ForeignKey("streamers.id"), nullable=False, index=True)
    video_id = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(400), nullable=False)
    published_at = db.Column(db.DateTime(timezone=True))
    view_count = db.Column(db.BigInteger, nullable=False, default=0)
    like_count = db.Column(db.BigInteger, nullable=False, default=0)
    comment_count = db.Column(db.BigInteger, nullable=False, default=0)
    duration_iso8601 = db.Column(db.String(32))
    fetched_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("streamer_id", "video_id"),)


class DailyReviewSlot(db.Model):
    """One of five persistent review reservations for a New York calendar day."""
    __tablename__ = "daily_review_slots"
    id = db.Column(db.Integer, primary_key=True)
    review_date = db.Column(db.Date, nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    clip_id = db.Column(db.Integer, db.ForeignKey("clips.id"), nullable=False)
    __table_args__ = (
        db.CheckConstraint("slot >= 1 AND slot <= 5", name="ck_review_slot_range"),
        UniqueConstraint("review_date", "slot", name="uq_review_date_slot"),
        UniqueConstraint("clip_id", name="uq_review_clip"),
    )
