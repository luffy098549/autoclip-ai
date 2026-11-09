"""Owner-only integration readiness, never exposing secrets."""
import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify
from ..models import db
from ..security import admin_only

integrations_bp = Blueprint("integrations", __name__)


@integrations_bp.get("/integrations")
@admin_only
def integration_readiness():
    storage = Path(current_app.config["MEDIA_ROOT"])
    token_file = storage / "private" / "youtube-token.json"
    return jsonify(
        deployment={
            "read_only_demo": bool(current_app.config.get("READ_ONLY_DEPLOYMENT")),
            "database": db.engine.dialect.name,
        },
        youtube={
            "local_oauth_token_present": token_file.is_file(),
            "metadata_api_key_present": bool(os.getenv("YOUTUBE_API_KEY")),
            "manual_uploader_available": True,
            "automatic_publishing_enabled": False,
        },
        tiktok={
            "account_access_token_configured": bool(os.getenv("TIKTOK_ACCESS_TOKEN")),
            "developer_audit_confirmed": False,
            "automatic_publishing_enabled": False,
        },
        instagram={
            "professional_account_configured": bool(os.getenv("INSTAGRAM_USER_ID")),
            "token_configured": bool(os.getenv("INSTAGRAM_ACCESS_TOKEN")),
            "owned_media_host_configured": bool(os.getenv("INSTAGRAM_MEDIA_HOST")),
            "automatic_publishing_enabled": False,
        },
        note="Presence flags only: account authorization and API availability are not verified.",
    )
