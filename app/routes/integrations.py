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
