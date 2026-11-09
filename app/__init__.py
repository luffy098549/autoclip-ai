"""Flask application factory for AutoClip AI."""
import os
import secrets
from flask import Flask, jsonify
from flask_wtf.csrf import CSRFProtect
from .models import db

csrf = CSRFProtect()


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///autoclip.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
        ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD_HASH", ""),
        MEDIA_ROOT=os.getenv("MEDIA_ROOT", os.path.abspath("storage")),
        MAX_CONTENT_LENGTH=500 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PUBLISHING_ENABLED=False,
        PROCESSING_ENABLED=os.getenv("PROCESSING_ENABLED", "false").lower() == "true",
        AI_ENABLED=os.getenv("AI_ENABLED", "false").lower() == "true",
        AUTO_RENDER_ENABLED=os.getenv("AUTO_RENDER_ENABLED", "false").lower() == "true",
    )
    if config:
        app.config.update(config)
    if (app.config.get("ADMIN_PASSWORD_HASH") and
            app.config["SECRET_KEY"] == "replace-with-unique-random-secret"):
        raise RuntimeError("Set a strong SECRET_KEY before enabling admin login")
    db.init_app(app)
    csrf.init_app(app)

    from .security import auth_bp
    from .routes import dashboard_bp, api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return jsonify(status="ok", name="AutoClip AI")

    return app
