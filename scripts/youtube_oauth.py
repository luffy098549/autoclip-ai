"""Owner-initiated YouTube OAuth authorization.

Use --manual in remote environments such as GitHub Codespaces. Never commit
client secrets or tokens, and never share authorization callback URLs.
"""
import argparse
import getpass
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.publishers.youtube import SCOPES


def main():
    parser = argparse.ArgumentParser(description="Authorize your own YouTube channel")
    parser.add_argument("--client-secrets", default="storage/private/youtube-client.json")
    parser.add_argument("--token", default="storage/private/youtube-token.json")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--manual", action="store_true",
                        help="Use a private copy/paste callback flow in remote Codespaces")
    args = parser.parse_args()
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise SystemExit("Install requirements-social.txt first") from exc

    client_file = Path(args.client_secrets).expanduser().resolve()
    token_file = Path(args.token).expanduser().resolve()
    if not client_file.is_file():
        raise SystemExit("Put Google OAuth client JSON in storage/private; never commit it")
    token_file.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(token_file.parent, 0o700)
    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), scopes=list(SCOPES))

    if args.manual:
        # Loopback redirects are permitted for Google Desktop OAuth clients.
        # The browser may display connection refused; the URL still contains
        # the callback data. Do not send that URL to anyone.
        flow.redirect_uri = f"http://localhost:{args.port}/"
        auth_url, expected_state = flow.authorization_url(
            access_type="offline", prompt="consent"
        )
        print("Open this Google authorization URL in your own browser:")
        print(auth_url)
        print("\nAfter consenting, localhost may show a connection error.")
        print("Copy the ENTIRE URL from the browser address bar.")
        print("Paste it into the hidden prompt below; never share it in chat.")
        callback = getpass.getpass("Private callback URL: ").strip()
        parsed = urlparse(callback)
        if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1")
                or parsed.port != args.port or parsed.path not in ("", "/")):
            raise SystemExit("Unexpected callback address. Authorization cancelled.")
        params = parse_qs(parsed.query)
        if params.get("state", [None])[0] != expected_state:
            raise SystemExit("OAuth state mismatch. Authorization cancelled.")
        if "error" in params or not params.get("code"):
            raise SystemExit("Google did not return an authorization code.")
        flow.fetch_token(authorization_response=callback)
        credentials = flow.credentials
    else:
        credentials = flow.run_local_server(
            host="localhost", port=args.port, open_browser=True
        )

    if not credentials.refresh_token:
        raise SystemExit("No refresh token received. Review OAuth consent configuration.")
    with os.fdopen(os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as file:
        file.write(credentials.to_json())
    token_file.chmod(0o600)
    print("YouTube channel authorization saved privately at:", token_file)


if __name__ == "__main__":
    main()
