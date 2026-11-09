"""Runs only in the GitHub Actions PostgreSQL integration job."""
import os

import pytest
from sqlalchemy import inspect, text

from app import create_app
from app.models import db, Streamer, MediaSource, Clip, Publication

pytestmark=pytest.mark.skipif(
    not os.getenv("DATABASE_URL","").startswith("postgresql"),
    reason="Integration test requires PostgreSQL DATABASE_URL",
)


def test_postgres_migrated_schema_and_foreign_keys():
    app=create_app({"TESTING":True})
    with app.app_context():
        assert db.engine.dialect.name=="postgresql"
        inspector=inspect(db.engine)
        assert {
            "streamers","sources","clips","publications",
            "performance_metrics","transcript_segments",
            "competitor_videos","alembic_version",
        }.issubset(set(inspector.get_table_names()))
        assert db.session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()=="20261109_001"


def test_postgres_transaction_roundtrip():
    app=create_app({"TESTING":True})
    with app.app_context():
        creator=Streamer(
            display_name="Prueba temporal",platform="youtube",
            channel_identifier="test-ci-transaction",active=False,
        )
        db.session.add(creator)
        db.session.flush()
        source=MediaSource(
            streamer_id=creator.id,source_uri="sample-owned-ci.mp4",
            rights_status="owned",permission_evidence="CI generated media",
        )
        db.session.add(source)
        db.session.flush()
        clip=Clip(
            source_id=source.id,start_seconds=0,end_seconds=15,
            editorial_status="ready",
        )
        db.session.add(clip)
        db.session.flush()
        item=Publication(
            clip_id=clip.id,platform="youtube",scheduled_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            state="planned",idempotency_key="postgres-integration-ci",
        )
        db.session.add(item)
        db.session.flush()
        assert item.id is not None
        db.session.rollback()
        assert Streamer.query.filter_by(channel_identifier="test-ci-transaction").first() is None
