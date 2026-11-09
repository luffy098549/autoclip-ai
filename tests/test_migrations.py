"""Verify that the committed Alembic migration creates the expected tables."""
from sqlalchemy import inspect, text
from flask_migrate import upgrade

from app import create_app
from app.models import db


EXPECTED={
    "streamers","sources","clips","publications",
    "transcript_segments","performance_metrics","competitor_videos","daily_review_slots","alembic_version"
}


def test_initial_migration_sqlite(tmp_path):
    path=tmp_path/"migrations-test.sqlite"
    app=create_app({
        "TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///"+str(path),
        "SECRET_KEY":"test-secret", "WTF_CSRF_ENABLED":False,
    })
    with app.app_context():
        upgrade()
        tables=set(inspect(db.engine).get_table_names())
        assert EXPECTED.issubset(tables)
        revision=db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision=="20261109_002"
        upgrade()  # applying migrations twice must be safe and idempotent
        assert db.session.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar_one()==1
