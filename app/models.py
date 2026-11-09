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
