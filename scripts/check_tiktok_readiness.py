"""Read-only deployment readiness checks for TikTok application review.

Does not print environment values or credentials. Run with:
    python -m scripts.check_tiktok_readiness
"""
import ipaddress
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

PATHS = ("/about", "/terms", "/privacy")
DRAFT_MARKERS = (b"legal draft", b"not final", b"draft for review", b"placeholder", b"lorem ipsum", b"to be added", b"to be finalized")


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


class RobotsParser(HTMLParser):
    """Parse robots directives independent of attribute order, case and quoting."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        values = dict(attrs)
        if values.get("name", "").lower() in ("robots", "googlebot", "bingbot"):
            directives = values.get("content") or ""
            if "noindex" in [part.strip().lower() for part in directives.split(",")]:
                self.noindex = True


def has_noindex(content, robots_header=""):
    directives = [part.strip().lower() for part in robots_header.split(",")]
    if "noindex" in directives:
        return True
    parser = RobotsParser()
    parser.feed(content.decode("utf-8", errors="replace"))
    return parser.noindex


def assess(origin, fetch):
    """Return issue codes only; never echo page contents, URLs or tokens."""
    issues = []
    if not valid_public_origin(origin):
        return ["public_https_origin_required"]
    for path in PATHS:
        try:
            result = fetch(origin + path)
            status, content, content_type = result[:3]
            robots_header = result[3] if len(result) > 3 else ""
        except Exception:
            issues.append(path[1:] + "_unreachable")
            continue
        if status != 200:
            issues.append(path[1:] + "_http_error")
        elif len(content) > 256_000:
            issues.append(path[1:] + "_oversized_response")
        elif b"<html" not in content.lower() or "text/html" not in content_type.lower():
            issues.append(path[1:] + "_invalid_html")
        elif path != "/about" and any(marker in content.lower() for marker in DRAFT_MARKERS):
            issues.append(path[1:] + "_legal_draft")
        elif path != "/about" and has_noindex(content, robots_header):
            issues.append(path[1:] + "_legal_noindex")
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
            return response.status, response.read(256_001), response.headers.get("Content-Type", ""), response.headers.get("X-Robots-Tag", "")
    except HTTPError as exc:
        return exc.code, b"", exc.headers.get("Content-Type", ""), exc.headers.get("X-Robots-Tag", "")


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
