from scripts.check_tiktok_readiness import assess, valid_public_origin


def test_public_origin_requires_https_and_no_credentials():
    for origin in ("", "http://example.com", "https://localhost", "https://127.0.0.1",
                   "https://user:pass@example.com", "https://example.com/path",
                   "https://example.com?token=x", "https://example.com/#x",
                   "https://example.com trailing"):
        assert not valid_public_origin(origin)
    assert valid_public_origin("https://autoclip.example.com")


def test_readiness_fails_closed_for_legal_drafts():
    def fetch(url):
        if url.endswith("/about"):
            return 200, b"<html>Welcome</html>", "text/html"
        return 200, b"<html>LEGAL DRAFT - NOT FINAL</html>", "text/html"
    assert assess("https://autoclip.example.com", fetch) == ["terms_legal_draft", "privacy_legal_draft"]


def test_readiness_rejects_http_errors_and_non_html():
    def fetch(url):
        if url.endswith("/about"):
            return 404, b"missing", "text/html"
        if url.endswith("/terms"):
            return 200, b"not html", "text/plain"
        raise OSError("offline")
    assert assess("https://autoclip.example.com", fetch) == [
        "about_http_error", "terms_invalid_html", "privacy_unreachable"]


def test_readiness_accepts_pages_without_draft_markers():
    def fetch(url):
        return 200, b"<!doctype html><html lang='en'>Approved text</html>", "text/html; charset=utf-8"
    assert assess("https://autoclip.example.com", fetch) == []


def test_readiness_rejects_private_reserved_and_placeholder_origins():
    for origin in (
        "https://10.0.0.1", "https://192.168.1.1", "https://172.16.0.1",
        "https://169.254.169.254", "https://[::1]", "https://[fc00::1]",
        "https://example.com:8443", "https://autoclip.example",
        "https://autoclip.test", "https://internal.local",
    ):
        assert not valid_public_origin(origin), origin
    assert valid_public_origin("https://autoclip.example.com:443")


def test_readiness_rejects_oversized_html():
    def fetch(url):
        return 200, b"<html>" + b"x" * 256_000, "text/html"
    assert assess("https://autoclip.example.com", fetch) == [
        "about_oversized_response", "terms_oversized_response", "privacy_oversized_response"
    ]


def test_redirect_handler_never_follows_redirects():
    from scripts.check_tiktok_readiness import NoRedirects
    handler = NoRedirects()
    assert handler.redirect_request(None, None, 302, "Found", {},
                                    "http://169.254.169.254/") is None
    assert handler.redirect_request(None, None, 301, "Moved", {},
                                    "https://another-domain.com/") is None


def test_readiness_rejects_redirect_status():
    def fetch(url):
        return 302, b"", "text/html"
    assert assess("https://autoclip.example.com", fetch) == [
        "about_http_error", "terms_http_error", "privacy_http_error"
    ]
