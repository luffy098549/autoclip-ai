"""Owner-initiated local OAuth flow. Run on your own machine, not in a cloud worker."""
import argparse
import os
from pathlib import Path

from app.publishers.youtube import SCOPES


def main():
    parser = argparse.ArgumentParser(description="Authorize your own YouTube channel")
    parser.add_argument("--client-secrets", default="storage/private/youtube-client.json")
    parser.add_argument("--token", default="storage/private/youtube-token.json")
    parser.add_argument("--port", type=int, default=8765)
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
    credentials = flow.run_local_server(host="localhost", port=args.port, open_browser=True)
    if not credentials.refresh_token:
        raise SystemExit("No refresh token received. Review OAuth consent configuration.")
    with os.fdopen(os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as file:
        file.write(credentials.to_json())
    token_file.chmod(0o600)
    print("YouTube channel authorization saved privately at:", token_file)


if __name__ == "__main__":
    main()
