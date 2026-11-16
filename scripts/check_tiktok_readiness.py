"""Read-only deployment readiness checks for TikTok application review.

Does not print environment values or credentials. Run with:
    python -m scripts.check_tiktok_readiness
"""
import ipaddress
import os
import sys
from urllib.parse import urlsplit
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

PATHS = ("/about", "/terms", "/privacy")
DRAFT_MARKERS = (b"LEGAL DRAFT", b"NOT FINAL", b"Draft for review")


def valid_public_origin(value):
    if not value or any(c.isspace() for c in value):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if not host or host.endswith('.') or '.' not in host or host.endswith(('.local', '.internal', '.test', '.invalid', '.example')):
            return False
        try:
            if not ipaddress.ip_address(host).is_global:
                return False
        except ValueError:
            pass  # DNS names are allowed; the operator must control the domain.
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and parsed.port in (None, 443)
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
        elif len(content) > 256_000:
            issues.append(path[1:] + "_oversized_response")
        elif b"<html" not in content.lower() or "text/html" not in content_type.lower():
            issues.append(path[1:] + "_invalid_html")
        elif path != "/about" and any(marker in content for marker in DRAFT_MARKERS):
            issues.append(path[1:] + "_legal_draft")
    return issues


class NoRedirects(HTTPRedirectHandler):
    """Never follow a redirect from the expected public HTTPS origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_page(url):
    request = Request(url, headers={"User-Agent": "AutoClip-readiness/1.0"})
    opener = build_opener(NoRedirects())
    try:
        with opener.open(request, timeout=8) as response:
            return response.status, response.read(256_001), response.headers.get("Content-Type", "")
    except HTTPError as exc:
        return exc.code, b"", exc.headers.get("Content-Type", "")


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
