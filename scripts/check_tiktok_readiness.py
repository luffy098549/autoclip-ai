"""Read-only deployment readiness checks for TikTok application review.

Does not print environment values or credentials. Run with:
    python -m scripts.check_tiktok_readiness
"""
import os
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

PATHS = ("/about", "/terms", "/privacy")
DRAFT_MARKERS = (b"LEGAL DRAFT", b"NOT FINAL", b"Draft for review")


def valid_public_origin(value):
    if not value or any(c.isspace() for c in value):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and not parsed.path.strip("/") and not parsed.query and not parsed.fragment
                and parsed.hostname not in ("localhost", "127.0.0.1", "::1"))
    except ValueError:
        return False


def assess(origin, fetch):
    """Return issue codes only; never echo page contents, URLs or tokens."""
    issues = []
    if not valid_public_origin(origin):
        return ["public_https_origin_required"]
    for path in PATHS:
        try:
            status, content, content_type = fetch(origin + path)
        except Exception:
            issues.append(path[1:] + "_unreachable")
            continue
        if status != 200:
            issues.append(path[1:] + "_http_error")
        elif b"<html" not in content.lower() or "text/html" not in content_type.lower():
            issues.append(path[1:] + "_invalid_html")
        elif path != "/about" and any(marker in content for marker in DRAFT_MARKERS):
            issues.append(path[1:] + "_legal_draft")
    return issues


def fetch_page(url):
    request = Request(url, headers={"User-Agent": "AutoClip-readiness/1.0"})
    with urlopen(request, timeout=8) as response:
        return response.status, response.read(256_000), response.headers.get("Content-Type", "")


def main():
    origin = os.getenv("AUTOCLIP_PUBLIC_ORIGIN", "")
    issues = assess(origin, fetch_page)
    for issue in issues:
        print("NOT READY:", issue)
    if issues:
        return 1
    print("Public pages reachable and legal draft markers absent.")
    print("NOTE: OAuth, ownership verification, legal accuracy and TikTok approval require separate checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
