"""Authenticated operational status; never expose tokens or private settings."""
import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..models import db
from ..scheduler import MAX_PER_DAY, MIN_INTERVAL, TIMEZONE
from ..security import admin_only

system_bp = Blueprint("system", __name__)


@system_bp.get("/system")
@admin_only
def system_status():
    app = current_app
    try:
        db.session.execute(text("SELECT 1"))
        database_connected = True
        database_error = None
    except SQLAlchemyError:
        db.session.rollback()
        database_connected = False
        database_error = "No se pudo establecer conexión con la base de datos"
    dialect = db.engine.dialect.name
    result = {
        "version": "0.5.0",
        "database": {
            "dialect": dialect,
            "engine": "PostgreSQL" if dialect == "postgresql" else "SQLite (solo desarrollo)",
            "connected": database_connected,
            "message": database_error,
        },
        "owner_login_configured": bool(app.config.get("ADMIN_PASSWORD_HASH")),
        "media_storage_available": Path(app.config["MEDIA_ROOT"]).is_dir(),
        "processing_enabled": bool(app.config.get("PROCESSING_ENABLED")),
        "ai_enabled": bool(app.config.get("AI_ENABLED")),
        "auto_render_enabled": bool(app.config.get("AUTO_RENDER_ENABLED")),
        "youtube_monitoring_enabled": bool(
            app.config.get("MONITORING_ENABLED") and os.getenv("YOUTUBE_API_KEY")
        ),
        "social_publishing_enabled": False,
        "time_zone": str(TIMEZONE),
        "interval_minutes": int(MIN_INTERVAL.total_seconds() / 60),
        "daily_limit": MAX_PER_DAY,
    }
    return jsonify(result), 200 if database_connected else 503
