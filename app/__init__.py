"""Flask application factory for AutoClip AI."""
import os
from flask import Flask, jsonify
from .models import db


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///autoclip.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv("SECRET_KEY", "development-only-change-me"),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        PUBLISHING_ENABLED=False,
    )
    if config:
        app.config.update(config)
    db.init_app(app)

    from .routes import dashboard_bp, api_bp
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return jsonify(status="ok", name="AutoClip AI")

    return app
