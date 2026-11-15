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
    authorization_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="false"
    )
    session["youtube_oauth_state"] = state
    return redirect(authorization_url)


@integrations_bp.get("/integrations/youtube/callback")
@admin_only
def youtube_callback():
    if current_app.config.get("READ_ONLY_DEPLOYMENT"):
        return jsonify(error="Modo de solo lectura"), 403
    expected = session.pop("youtube_oauth_state", None)
    received = request.args.get("state", "")
    if not expected or not secrets.compare_digest(expected, received):
        return jsonify(error="Estado OAuth inválido o caducado"), 400
    if request.args.get("error"):
        return jsonify(error="Google no autorizó la conexión"), 400
    try:
        flow = _youtube_flow()
        # Never trust an arbitrary Host header as an OAuth redirect URI.
        redirect_uri = flow.redirect_uri
        if request.base_url != redirect_uri:
            return jsonify(error="URL de retorno no coincide con la configurada"), 400
        flow.fetch_token(authorization_response=request.url)
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

@integrations_bp.get("/integrations/youtube/connect")
@admin_only
def youtube_connect():
    """Start an owner-initiated OAuth flow for the configured web client."""
    from flask import abort, redirect, session, url_for
    from google_auth_oauthlib.flow import Flow
    from ..publishers.youtube import SCOPES

    if current_app.config.get("READ_ONLY_DEPLOYMENT"):
        abort(403)
    storage = Path(current_app.config["MEDIA_ROOT"]) / "private"
    client_file = storage / "youtube-client.json"
    if not client_file.is_file():
        return jsonify(error="Missing private YouTube web OAuth client JSON"), 503
    flow = Flow.from_client_secrets_file(
        str(client_file), scopes=list(SCOPES),
        redirect_uri=url_for("integrations.youtube_callback", _external=True, _scheme="https"),
    )
    url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    session["youtube_oauth_state"] = state
    return redirect(url)


@integrations_bp.get("/integrations/youtube/callback")
@admin_only
def youtube_callback():
    """Exchange the authorization code only after checking OAuth state."""
    import os
    import secrets
    from flask import abort, request, session, url_for
    from google_auth_oauthlib.flow import Flow
    from ..publishers.youtube import SCOPES

    if current_app.config.get("READ_ONLY_DEPLOYMENT"):
        abort(403)
    expected = session.pop("youtube_oauth_state", None)
    supplied = request.args.get("state", "")
    if not expected or not secrets.compare_digest(expected, supplied):
        return jsonify(error="Invalid or expired OAuth state"), 400
    if request.args.get("error"):
        return jsonify(error="Google authorization was not completed"), 400
    if not request.args.get("code"):
        return jsonify(error="Missing Google authorization code"), 400
    storage = Path(current_app.config["MEDIA_ROOT"]) / "private"
    client_file = storage / "youtube-client.json"
    if not client_file.is_file():
        return jsonify(error="Missing private YouTube web OAuth client JSON"), 503
    flow = Flow.from_client_secrets_file(
        str(client_file), scopes=list(SCOPES),
        state=expected,
        redirect_uri=url_for("integrations.youtube_callback", _external=True, _scheme="https"),
    )
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception:
        current_app.logger.exception("YouTube OAuth exchange failed")
        return jsonify(error="Google authorization exchange failed"), 400
    credentials = flow.credentials
    if not credentials.refresh_token:
        return jsonify(error="No refresh token received; reconnect with consent"), 400
    storage.mkdir(parents=True, exist_ok=True)
    token_file = storage / "youtube-token.json"
    tmp_file = storage / ("youtube-token-" + secrets.token_hex(8) + ".tmp")
    try:
        with os.fdopen(os.open(tmp_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as handle:
            handle.write(credentials.to_json())
        os.replace(tmp_file, token_file)
        token_file.chmod(0o600)
    finally:
        tmp_file.unlink(missing_ok=True)
    return jsonify(connected=True, service="youtube", publishing_enabled=False)
