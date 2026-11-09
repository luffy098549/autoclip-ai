"""Safe read-only status endpoints; publishing and ingestion are intentionally OFF."""
from flask import Blueprint, jsonify
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from ..models import db, Streamer, MediaSource, Clip, Publication
from ..scheduler import MAX_PER_DAY, MIN_INTERVAL, PLATFORMS, TIMEZONE

api_bp = Blueprint("api", __name__)


@api_bp.get("/status")
def status():
    return jsonify(
        project="AutoClip AI",
        version="0.2.0",
        publishing_enabled=False,
        ingestion_enabled=False,
        ai_detection_enabled=False,
        platforms=list(PLATFORMS),
        interval_minutes=int(MIN_INTERVAL.total_seconds() / 60),
        daily_limit_per_platform=MAX_PER_DAY,
        timezone=str(TIMEZONE),
        note="MVP dashboard and manual source processing only; online publishing unavailable.",
    )


@api_bp.get("/summary")
def summary():
    """Return counts without making the dashboard crash before database initialization."""
    counts = {"streamers": 0, "sources": 0, "clips": 0, "publications": 0}
    models = {"streamers": Streamer, "sources": MediaSource,
              "clips": Clip, "publications": Publication}
    try:
        for name, model in models.items():
            counts[name] = db.session.query(func.count(model.id)).scalar() or 0
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(configured=False, counts=counts,
                       message="Initialize database with python -m scripts.init_db")
    return jsonify(configured=True, counts=counts, message="Database connected")
