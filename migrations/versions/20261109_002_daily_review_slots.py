"""Persist daily manual-review reservations (maximum five per New York day)."""
from alembic import op
import sqlalchemy as sa

revision = "20261109_002"
down_revision = "20261109_001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "daily_review_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("clip_id", sa.Integer(), sa.ForeignKey("clips.id"), nullable=False),
        sa.CheckConstraint("slot >= 1 AND slot <= 5", name="ck_review_slot_range"),
        sa.UniqueConstraint("review_date", "slot", name="uq_review_date_slot"),
        sa.UniqueConstraint("clip_id", name="uq_review_clip"),
    )


def downgrade():
    op.drop_table("daily_review_slots")
