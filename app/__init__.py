"""Flask application factory for AutoClip AI."""
import os
import secrets
from flask import Flask, jsonify, request
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from .models import db

csrf = CSRFProtect()
migrate = Migrate()


def normalized_database_url(url):
    # Render provides postgresql:// URLs, which otherwise select the uninstalled psycopg2.
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=normalized_database_url(os.getenv("DATABASE_URL", "postgresql+psycopg://autoclip:autoclip@db:5432/autoclip")),
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
        AUTO_CAPTION_ENABLED=os.getenv("AUTO_CAPTION_ENABLED", "false").lower() == "true",
        MONITORING_ENABLED=os.getenv("MONITORING_ENABLED", "false").lower() == "true",
        READ_ONLY_DEPLOYMENT=os.getenv("READ_ONLY_DEPLOYMENT", "false").lower() == "true",
    )
    if config:
        app.config.update(config)
    if (app.config.get("ADMIN_PASSWORD_HASH") and
            app.config["SECRET_KEY"] == "replace-with-unique-random-secret"):
        raise RuntimeError("Set a strong SECRET_KEY before enabling admin login")
    @app.before_request
    def block_writes_in_read_only_demo():
        if (app.config.get("READ_ONLY_DEPLOYMENT")
                and request.path.startswith("/api/")
                and request.method not in ("GET", "HEAD", "OPTIONS")):
            return jsonify(error="Esta demostración pública es de solo lectura"), 403

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from .security import auth_bp
    from .routes import dashboard_bp, api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    from .routes.planning import planning_bp
    app.register_blueprint(planning_bp, url_prefix="/api")
    from .routes.previews import previews_bp
    app.register_blueprint(previews_bp, url_prefix="/api")
    from .routes.system import system_bp
    app.register_blueprint(system_bp, url_prefix="/api")

    @app.after_request
    def secure_browser_response(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; media-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'; base-uri 'none'")
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok", name="AutoClip AI")

    return app
