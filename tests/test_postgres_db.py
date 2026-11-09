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
        ).scalar_one()=="20261109_002"


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


def test_postgres_rejects_orphan_clip_and_recovers_transaction():
    """A clip cannot reference a missing source; rollback restores the session."""
    from sqlalchemy.exc import IntegrityError

    app = create_app({"TESTING": True})
    with app.app_context():
        # The negative ID is deliberately absent from a fresh CI database.
        missing_source_id = -987654321
        assert db.session.execute(
            text("SELECT count(*) FROM sources WHERE id = :id"),
            {"id": missing_source_id},
        ).scalar_one() == 0
        try:
            db.session.add(Clip(
                source_id=missing_source_id,
                start_seconds=0,
                end_seconds=5,
            ))
            with pytest.raises(IntegrityError):
                db.session.flush()
        finally:
            db.session.rollback()
        # A query after rollback confirms the session is usable again.
        assert db.session.execute(text("SELECT 1")).scalar_one() == 1


def test_postgres_rejects_duplicate_streamer_identity():
    """Streamer identity is unique per platform, even across separate rows."""
    from uuid import uuid4
    from sqlalchemy.exc import IntegrityError

    app = create_app({"TESTING": True})
    with app.app_context():
        channel = f"ci-streamer-{uuid4().hex}"
        try:
            db.session.add(Streamer(
                display_name="Synthetic CI streamer", platform="youtube",
                channel_identifier=channel, active=False,
            ))
            db.session.flush()
            db.session.add(Streamer(
                display_name="Duplicate synthetic streamer", platform="youtube",
                channel_identifier=channel, active=False,
            ))
            with pytest.raises(IntegrityError):
                db.session.flush()
        finally:
            db.session.rollback()

        assert db.session.execute(
            text("SELECT count(*) FROM streamers WHERE channel_identifier = :channel"),
            {"channel": channel},
        ).scalar_one() == 0
        assert db.session.execute(text("SELECT 1")).scalar_one() == 1


def test_postgres_allows_same_channel_identifier_on_different_platforms():
    """Uniqueness is scoped to a platform, not global across providers."""
    from uuid import uuid4

    app = create_app({"TESTING": True})
    with app.app_context():
        channel = f"ci-cross-platform-{uuid4().hex}"
        try:
            first = Streamer(
                display_name="Synthetic YouTube channel",
                platform="youtube", channel_identifier=channel, active=False,
            )
            second = Streamer(
                display_name="Synthetic Twitch channel",
                platform="twitch", channel_identifier=channel, active=False,
            )
            db.session.add_all([first, second])
            db.session.flush()
            assert first.id != second.id
            assert db.session.execute(
                text("SELECT count(*) FROM streamers WHERE channel_identifier = :channel"),
                {"channel": channel},
            ).scalar_one() == 2
        finally:
            db.session.rollback()

        assert db.session.execute(
            text("SELECT count(*) FROM streamers WHERE channel_identifier = :channel"),
            {"channel": channel},
        ).scalar_one() == 0


def test_postgres_rejects_duplicate_competitor_video_per_streamer():
    """Metadata imports cannot create duplicate video rows for one streamer."""
    from uuid import uuid4
    from sqlalchemy.exc import IntegrityError
    from app.models import CompetitorVideo

    app = create_app({"TESTING": True})
    with app.app_context():
        channel = f"ci-competitor-{uuid4().hex}"
        try:
            streamer = Streamer(
                display_name="Synthetic CI streamer", platform="youtube",
                channel_identifier=channel, active=False,
            )
            db.session.add(streamer)
            db.session.flush()
            for _ in range(2):
                db.session.add(CompetitorVideo(
                    streamer_id=streamer.id, video_id="synthetic-video-id",
                    title="Synthetic metadata only", view_count=0,
                ))
                if _ == 0:
                    db.session.flush()
            with pytest.raises(IntegrityError):
                db.session.flush()
        finally:
            db.session.rollback()

        assert db.session.execute(
            text("SELECT count(*) FROM streamers WHERE channel_identifier = :channel"),
            {"channel": channel},
        ).scalar_one() == 0
        assert db.session.execute(text("SELECT 1")).scalar_one() == 1
