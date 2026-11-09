import os
from flask import Flask, jsonify
from .models import db


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///autoclip.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv("SECRET_KEY", "development-only-change-me"),
    )
    if config:
        app.config.update(config)
    db.init_app(app)

    @app.get("/health")
    def health():
        return jsonify(status="ok", name="AutoClip AI")

    @app.get("/api/status")
    def status():
        return jsonify(
            project="AutoClip AI", version="0.1.0",
            publishing_enabled=False,
            platforms=["youtube", "tiktok", "instagram"],
            interval_minutes=120, daily_limit_per_platform=5,
            note="Scaffold only: uploads are not connected.",
        )
    return app
