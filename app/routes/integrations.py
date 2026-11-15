"""Owner-only integration readiness and explicit YouTube web OAuth."""
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from flask import Blueprint, current_app, jsonify, redirect, request, session
from ..models import db
from ..security import admin_only

integrations_bp = Blueprint("integrations", __name__)


def _youtube_oauth_config():
    client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", "").strip()
    if not all((client_id, client_secret, redirect_uri)):
        raise ValueError("Configura YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET y YOUTUBE_REDIRECT_URI")
    parsed = urlsplit(redirect_uri)
    if (parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1"))):
        raise ValueError("La URL de retorno debe usar HTTPS")
    if parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.path != "/api/integrations/youtube/callback":
        raise ValueError("YOUTUBE_REDIRECT_URI no corresponde a la ruta OAuth")
    return client_id, client_secret, redirect_uri


def _youtube_flow():
    from google_auth_oauthlib.flow import Flow
    from ..publishers.youtube import SCOPES
    client_id, client_secret, redirect_uri = _youtube_oauth_config()
    flow = Flow.from_client_config(
        {"web": {"client_id": client_id, "client_secret": client_secret,
                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                 "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=list(SCOPES),
        redirect_uri=redirect_uri,
    )
    return flow


@integrations_bp.get("/integrations/youtube/connect")
@admin_only
def youtube_connect():
    if current_app.config.get("READ_ONLY_DEPLOYMENT"):
        return jsonify(error="Modo de solo lectura"), 403
    try:
        flow = _youtube_flow()
    except (ImportError, ValueError) as exc:
        return jsonify(error=str(exc)), 503
    # Persist PKCE verifier across the Google redirect and callback.
    flow.code_verifier = secrets.token_urlsafe(64)
    authorization_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="false"
    )
    session["youtube_oauth_state"] = state
    session["youtube_oauth_code_verifier"] = flow.code_verifier
    return redirect(authorization_url)


@integrations_bp.get("/integrations/youtube/callback")
@admin_only
def youtube_callback():
    if current_app.config.get("READ_ONLY_DEPLOYMENT"):
        return jsonify(error="Modo de solo lectura"), 403
    expected = session.pop("youtube_oauth_state", None)
    verifier = session.pop("youtube_oauth_code_verifier", None)
    received = request.args.get("state", "")
    if not expected or not verifier or not secrets.compare_digest(expected, received):
        return jsonify(error="Estado OAuth inválido o caducado"), 400
    if request.args.get("error"):
        return jsonify(error="Google no autorizó la conexión"), 400
    try:
        flow = _youtube_flow()
        flow.code_verifier = verifier
        # The external HTTPS redirect URI comes exclusively from trusted
        # configuration. Codespaces may replace Host and scheme internally,
        # so never compare the proxy-facing Host to the public redirect host.
        # Flask routing ensures this callback path; OAuth state is verified
        # above, and the token exchange uses the fixed configured redirect URI.
        # The configured HTTPS redirect URI is used during token exchange.
        code = request.args.get("code")
        if not code:
            return jsonify(error="Falta el código de autorización"), 400
        flow.fetch_token(code=code)
        credentials = flow.credentials
        if not credentials.refresh_token:
            return jsonify(error="Google no entregó un token de renovación"), 400
        storage = Path(current_app.config["MEDIA_ROOT"]) / "private"
        storage.mkdir(parents=True, exist_ok=True, mode=0o700)
        storage.chmod(0o700)
        path = storage / "youtube-token.json"
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as handle:
            handle.write(credentials.to_json())
        path.chmod(0o600)
    except (ImportError, ValueError) as exc:
        return jsonify(error="No se pudo completar OAuth", detail=type(exc).__name__), 400
    except Exception:
        current_app.logger.exception("YouTube OAuth callback failed")
        return jsonify(error="Falló la autorización de YouTube"), 502
    return redirect("/")


@integrations_bp.get("/integrations")
@admin_only
def integration_readiness():
    storage = Path(current_app.config["MEDIA_ROOT"])
    token_file = storage / "private" / "youtube-token.json"
    # Read-only local OAuth status; never expose token contents.
    token_status = "not_connected"
    if token_file.is_file() and token_file.stat().st_size > 0:
        try:
            from google.oauth2.credentials import Credentials
            credentials = Credentials.from_authorized_user_file(str(token_file))
            token_status = "authorized" if credentials.valid else (
                "refresh_required" if credentials.refresh_token else "reauthorization_required"
            )
        except (ValueError, OSError, KeyError):
            token_status = "reauthorization_required"
    return jsonify(
        deployment={
            "read_only_demo": bool(current_app.config.get("READ_ONLY_DEPLOYMENT")),
            "database": db.engine.dialect.name,
        },
        youtube={
            "local_oauth_token_present": token_file.is_file(),
            "local_oauth_status": token_status,
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


@integrations_bp.get("/integrations/youtube/uploads")
@admin_only
def youtube_upload_history():
    """Local audit history. Never expose credentials."""
    from ..models import Publication
    records = (Publication.query.filter_by(platform="youtube")
               .filter(Publication.state.in_(("publishing", "published", "upload_uncertain")))
               .order_by(Publication.id.desc()).limit(100).all())
    return jsonify(items=[{
        "clip_id": item.clip_id, "state": item.state,
        "video_id": item.external_id,
        "url": ("https://www.youtube.com/watch?v=" + item.external_id) if item.external_id else None,
    } for item in records])


@integrations_bp.post("/integrations/youtube/upload-private")
@admin_only
def youtube_upload_private():
    """Single owner-confirmed private upload, never scheduled or retried automatically."""
    from datetime import datetime, timezone
    from uuid import uuid4
    from sqlalchemy import text
    from ..models import Clip, MediaSource, Publication
    from ..services.rights import assess_rights
    from ..quality import validate_render
    from ..publishers.youtube import upload_short

    if current_app.config.get("READ_ONLY_DEPLOYMENT"):
        return jsonify(error="Modo solo lectura"), 403
    data = request.get_json(silent=True) or {}
    if data.get("confirm_private") is not True:
        return jsonify(error="Confirma expresamente la subida privada"), 400
    try:
        clip_id = int(data.get("clip_id"))
    except (ValueError, TypeError):
        return jsonify(error="Clip inválido"), 400
    title = data.get("title")
    description = data.get("description", "")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
        return jsonify(error="Título de 1 a 100 caracteres requerido"), 400
    if not isinstance(description, str) or len(description) > 5000:
        return jsonify(error="Descripción demasiado larga"), 400
    if not isinstance(data.get("made_for_kids"), bool):
        return jsonify(error="Indica si el video está dirigido a niños"), 400

    # Serialize concurrent requests, then reserve the clip before touching YouTube.
    if db.engine.dialect.name == "postgresql":
        db.session.execute(text("SELECT pg_advisory_xact_lock(:key)"),
                           {"key": 500000000 + clip_id})
    existing = (Publication.query.filter_by(clip_id=clip_id, platform="youtube")
                .filter(Publication.state.in_(("publishing", "published", "upload_uncertain")))
                .first())
    if existing:
        db.session.rollback()
        return jsonify(error="Ya existe una subida o intento pendiente de verificar para este clip",
                       state=existing.state, video_id=existing.external_id), 409
    clip = db.session.get(Clip, clip_id)
    if not clip or clip.editorial_status != "ready" or not clip.output_path:
        db.session.rollback()
        return jsonify(error="El clip no está listo"), 400
    source = db.session.get(MediaSource, clip.source_id)
    if not source or not assess_rights(source.rights_status, source.permission_evidence).allowed:
        db.session.rollback()
        return jsonify(error="Fuente sin autorización registrada"), 403
    root = (Path(current_app.config["MEDIA_ROOT"]) / "clips").resolve()
    video = Path(clip.output_path).resolve()
    if video.parent != root or not video.is_file() or video.suffix.lower() != ".mp4":
        db.session.rollback()
        return jsonify(error="MP4 no disponible"), 400
    try:
        validate_render(video)
    except Exception:
        db.session.rollback()
        return jsonify(error="El video no superó la validación de calidad"), 400
    token = Path(current_app.config["MEDIA_ROOT"]) / "private" / "youtube-token.json"
    if not token.is_file():
        db.session.rollback()
        return jsonify(error="Conecta YouTube primero"), 503

    record = Publication(
        clip_id=clip_id, platform="youtube", scheduled_at=datetime.now(timezone.utc),
        state="publishing", idempotency_key=uuid4().hex
    )
    db.session.add(record)
    db.session.commit()
    try:
        video_id = upload_short(str(video), title.strip(), description,
                                token_path=str(token), privacy_status="private",
                                made_for_kids=data["made_for_kids"])
    except Exception:
        # A network failure may happen after YouTube accepted the upload.
        # Block further attempts until the owner checks YouTube Studio.
        current_app.logger.exception("YouTube private upload failed or outcome unknown")
        record.state = "upload_uncertain"
        db.session.commit()
        return jsonify(error="No se pudo confirmar la subida. Revisa YouTube Studio antes de reintentar.",
                       state="upload_uncertain"), 502
    record.external_id = video_id
    record.published_at = datetime.now(timezone.utc)
    record.state = "published"
    db.session.commit()
    return jsonify(clip_id=clip_id, video_id=video_id,
                   url="https://www.youtube.com/watch?v=" + video_id,
                   privacy_requested="private", state="published"), 201
