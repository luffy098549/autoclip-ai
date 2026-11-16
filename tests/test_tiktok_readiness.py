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


def test_readiness_detects_case_insensitive_legal_drafts_and_placeholders():
    for unfinished in (b"legal draft", b"Not Final", b"DRAFT FOR REVIEW",
                       b"Lorem Ipsum", b"to be added", b"TO BE FINALIZED"):
        def fetch(url):
            if url.endswith("/about"):
                return 200, b"<html>About</html>", "text/html"
            return 200, b"<html>" + unfinished + b"</html>", "text/html"
        assert assess("https://autoclip.example.com", fetch) == [
            "terms_legal_draft", "privacy_legal_draft"
        ]


def test_readiness_rejects_legal_pages_with_noindex_meta():
    def fetch(url):
        if url.endswith("/about"):
            return 200, b"<html>About</html>", "text/html"
        return (200, b'<html><head><meta name="robots" content="noindex, nofollow"></head><body>Terms</body></html>', "text/html")
    assert assess("https://autoclip.example.com", fetch) == [
        "terms_legal_noindex", "privacy_legal_noindex"
    ]


def test_readiness_rejects_robots_meta_variants_and_header():
    variants = (
        b"<html><meta content='follow, noindex' name='ROBOTS'></html>",
        b"<html><META NAME=googlebot CONTENT='NOINDEX'></html>",
        b"<html><meta name='bingbot' content='noindex, follow'></html>",
    )
    for html in variants:
        def fetch(url):
            if url.endswith("/about"):
                return 200, b"<html>About</html>", "text/html"
            return 200, html, "text/html"
        assert assess("https://autoclip.example.com", fetch) == [
            "terms_legal_noindex", "privacy_legal_noindex"
        ]

    def header_fetch(url):
        return 200, b"<html>Legal</html>", "text/html", "noindex, nofollow"
    assert assess("https://autoclip.example.com", header_fetch) == [
        "terms_legal_noindex", "privacy_legal_noindex"
    ]


def test_readiness_does_not_reject_index_directive():
    def fetch(url):
        return 200, b"<html><meta name='robots' content='index, follow'></html>", "text/html", "index"
    assert assess("https://autoclip.example.com", fetch) == []


def test_readiness_rejects_scoped_and_semicolon_robots_directives():
    def fetch(url):
        if url.endswith("/about"):
            return 200, b"<html>About</html>", "text/html"
        return 200, b"<html>Legal</html>", "text/html", "googlebot: noindex; nofollow"
    assert assess("https://autoclip.example.com", fetch) == [
        "terms_legal_noindex", "privacy_legal_noindex"
    ]


def test_readiness_handles_missing_robots_meta_attributes():
    def fetch(url):
        return 200, b"<html><meta name><meta name='robots'><meta content='noindex'></html>", "text/html"
    assert assess("https://autoclip.example.com", fetch) == []


def test_readiness_ignores_non_noindex_tokens():
    def fetch(url):
        return 200, b"<html><meta name='robots' content='noindexing, index'></html>", "text/html", "notnoindex"
    assert assess("https://autoclip.example.com", fetch) == []


def test_public_origin_rejects_malformed_dns_names():
    for origin in (
        "https://bad_host.example.com",
        "https://-bad.example.com",
        "https://bad-.example.com",
        "https://example.123",
        "https://example.com%2f.evil.com",
        "https://example..com",
        "https://example.c",
        "https://éxample.com",
        "https://999.999.999.999",
        "https://example.com\\\\@evil.com",
    ):
        assert not valid_public_origin(origin), origin
    assert valid_public_origin("https://autoclip-ai.example.com")
    assert valid_public_origin("https://autoclip.example.com:443")


def test_readiness_rejects_misleading_html_media_types_and_tags():
    for body, media_type in (
        (b"<html>OK</html>", "text/html-malicious"),
        (b"<html>OK</html>", "application/xhtml+xml"),
        (b"<htmlfake>OK</htmlfake>", "text/html"),
        (b"<!-- <html -->", "text/plain"),
    ):
        def fetch(url):
            return 200, body, media_type
        assert assess("https://autoclip.example.com", fetch) == [
            "about_invalid_html", "terms_invalid_html", "privacy_invalid_html"
        ]


def test_readiness_accepts_case_insensitive_html_content_type_with_parameters():
    def fetch(url):
        return 200, b"<HTML lang='en'>Policy</HTML>", " Text/HTML ; charset=utf-8 "
    assert assess("https://autoclip.example.com", fetch) == []


def test_readiness_rejects_html_root_spoofed_in_comments_and_scripts():
    for fake_html in (
        b"<!-- <html>fake</html> -->",
        b"<script>const markup = '<html>fake</html>';</script>",
        b"<div data-example='<html>fake</html>'>Not an HTML document</div>",
    ):
        def fetch(url):
            return 200, fake_html, "text/html"
        assert assess("https://autoclip.example.com", fetch) == [
            "about_invalid_html", "terms_invalid_html", "privacy_invalid_html"
        ]


def test_readiness_accepts_real_html_root_after_comment():
    def fetch(url):
        return 200, b"<!-- <html>example</html> --><html><body>Real policy</body></html>", "text/html"
    assert assess("https://autoclip.example.com", fetch) == []


def test_readiness_fails_closed_on_malformed_fetch_results():
    malformed = (
        (),
        (200,),
        (200, "<html>wrong type</html>", "text/html"),
        (200, b"<html>ok</html>", None),
        (200, b"<html>ok</html>", "text/html", None),
        (True, b"<html>ok</html>", "text/html"),
    )
    for result in malformed:
        def fetch(url):
            return result
        assert assess("https://autoclip.example.com", fetch) == [
            "about_unreachable", "terms_unreachable", "privacy_unreachable"
        ]


def test_readiness_rejects_html_escaped_and_whitespace_split_draft_notices():
    variants = (
        b"<html>LEGAL&#32;DRAFT</html>",
        b"<html>not&#x20;final</html>",
        b"<html>draft\nfor\treview</html>",
    )
    for html in variants:
        def fetch(url):
            if url.endswith("/about"):
                return 200, b"<html>About</html>", "text/html"
            return 200, html, "text/html"
        assert assess("https://autoclip.example.com", fetch) == [
            "terms_legal_draft", "privacy_legal_draft"
        ]


def test_readiness_detects_draft_notice_split_by_html_tags():
    variants = (
        b"<html><body>Legal <strong>draft</strong></body></html>",
        b"<html><body>Not <span>final</span></body></html>",
        b"<html><body>Draft <em>for</em> review</body></html>",
    )
    for html in variants:
        def fetch(url):
            if url.endswith("/about"):
                return 200, b"<html>About</html>", "text/html"
            return 200, html, "text/html"
        assert assess("https://autoclip.example.com", fetch) == [
            "terms_legal_draft", "privacy_legal_draft"
        ]


def test_readiness_ignores_draft_words_in_comments_and_scripts():
    html = (b"<html><body>Final legal text"
            b"<!-- LEGAL DRAFT -->"
            b"<script>const note = 'not final';</script>"
            b"<style>/* draft for review */</style>"
            b"</body></html>")
    def fetch(url):
        return 200, html, "text/html"
    assert assess("https://autoclip.example.com", fetch) == []
