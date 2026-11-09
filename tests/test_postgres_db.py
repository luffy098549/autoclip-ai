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


def test_postgres_enforces_relationships_and_idempotency_constraints():
    """Verify important constraints exist in the migrated PostgreSQL schema."""
    app = create_app({"TESTING": True})
    with app.app_context():
        inspector = inspect(db.engine)
        expected_foreign_keys = {
            "sources": ("streamer_id", "streamers"),
            "clips": ("source_id", "sources"),
            "publications": ("clip_id", "clips"),
            "transcript_segments": ("source_id", "sources"),
            "performance_metrics": ("clip_id", "clips"),
            "competitor_videos": ("streamer_id", "streamers"),
        }
        for table, (column, parent) in expected_foreign_keys.items():
            foreign_keys = inspector.get_foreign_keys(table)
            assert any(
                key["constrained_columns"] == [column]
                and key["referred_table"] == parent
                for key in foreign_keys
            ), f"Missing foreign key: {table}.{column} -> {parent}"

        publication_uniques = inspector.get_unique_constraints("publications")
        publication_indexes = inspector.get_indexes("publications")
        assert any(
            constraint["column_names"] == ["idempotency_key"]
            for constraint in publication_uniques
        ) or any(
            index["column_names"] == ["idempotency_key"] and index.get("unique")
            for index in publication_indexes
        ), "Publication idempotency keys must be unique"


def test_postgres_rejects_duplicate_publication_idempotency_keys():
    """Exercise the real database constraint, not just schema introspection."""
    from datetime import datetime, timezone
    from uuid import uuid4
    from sqlalchemy.exc import IntegrityError

    app = create_app({"TESTING": True})
    with app.app_context():
        key = f"ci-duplicate-{uuid4().hex}"
        try:
            source = MediaSource(
                source_uri="ci-owned-fixture.mp4", rights_status="owned",
                permission_evidence="Synthetic CI fixture; no external download",
            )
            db.session.add(source)
            db.session.flush()
            clip = Clip(source_id=source.id, start_seconds=0, end_seconds=10)
            db.session.add(clip)
            db.session.flush()
            db.session.add(Publication(
                clip_id=clip.id, platform="youtube",
                scheduled_at=datetime.now(timezone.utc),
                state="planned", idempotency_key=key,
            ))
            db.session.flush()
            db.session.add(Publication(
                clip_id=clip.id, platform="youtube",
                scheduled_at=datetime.now(timezone.utc),
                state="planned", idempotency_key=key,
            ))
            with pytest.raises(IntegrityError):
                db.session.flush()
        finally:
            # PostgreSQL aborts the transaction after an integrity error.
            # Roll back every fixture row, including the first publication.
            db.session.rollback()
        assert db.session.execute(
            text("SELECT count(*) FROM publications WHERE idempotency_key = :key"),
            {"key": key},
        ).scalar_one() == 0
