"""Initial PostgreSQL/SQLite schema for AutoClip AI.

Revision ID: 20261109_001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "20261109_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "streamers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=False),
        sa.Column("channel_identifier", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("platform", "channel_identifier"),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("streamer_id", sa.Integer(), sa.ForeignKey("streamers.id"), nullable=True),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("rights_status", sa.String(length=30), nullable=False),
        sa.Column("permission_evidence", sa.Text(), nullable=True),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "clips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("editorial_status", sa.String(length=30), nullable=False),
    )
    op.create_table(
        "publications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clip_id", sa.Integer(), sa.ForeignKey("clips.id"), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=True),
    )
    op.create_index("ix_transcript_segments_source_id", "transcript_segments", ["source_id"])
    op.create_table(
        "performance_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clip_id", sa.Integer(), sa.ForeignKey("clips.id"), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=False),
        sa.Column("views", sa.BigInteger(), nullable=False),
        sa.Column("likes", sa.BigInteger(), nullable=False),
        sa.Column("comments", sa.BigInteger(), nullable=False),
        sa.Column("shares", sa.BigInteger(), nullable=False),
        sa.Column("avg_watch_seconds", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_performance_metrics_clip_id", "performance_metrics", ["clip_id"])
    op.create_table(
        "competitor_videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("streamer_id", sa.Integer(), sa.ForeignKey("streamers.id"), nullable=False),
        sa.Column("video_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=400), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.BigInteger(), nullable=False),
        sa.Column("like_count", sa.BigInteger(), nullable=False),
        sa.Column("comment_count", sa.BigInteger(), nullable=False),
        sa.Column("duration_iso8601", sa.String(length=32), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("streamer_id", "video_id"),
    )
    op.create_index("ix_competitor_videos_streamer_id", "competitor_videos", ["streamer_id"])


def downgrade():
    op.drop_index("ix_competitor_videos_streamer_id", table_name="competitor_videos")
    op.drop_table("competitor_videos")
    op.drop_index("ix_performance_metrics_clip_id", table_name="performance_metrics")
    op.drop_table("performance_metrics")
    op.drop_index("ix_transcript_segments_source_id", table_name="transcript_segments")
    op.drop_table("transcript_segments")
    op.drop_table("publications")
    op.drop_table("clips")
    op.drop_table("sources")
    op.drop_table("streamers")
