"""Record when a clip worker atomically claimed a render."""
from alembic import op
import sqlalchemy as sa

revision = "20261122_003"
down_revision = "20261109_002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clips", sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("clips", "processing_started_at")
