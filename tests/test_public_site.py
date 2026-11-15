from app import create_app

def test_public_pages_are_accessible_without_login():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        for path, phrase in [("/about", b"More room for creativity"), ("/terms", b"Terms of Service"), ("/privacy", b"Privacy Policy")]:
            response = client.get(path)
            assert response.status_code == 200
            assert phrase in response.data
            assert b"Client secret" not in response.data

def test_legal_pages_are_marked_as_drafts():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        for path in ("/terms", "/privacy"):
            assert b"NOT FINAL" in client.get(path).data

def test_unfinalized_legal_text_is_not_indexed_or_cached():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        for path in ("/terms", "/privacy"):
            response = client.get(path)
            assert response.headers["X-Robots-Tag"] == "noindex, nofollow, noarchive"
            assert response.headers["Cache-Control"] == "no-store"
            assert response.headers["Content-Security-Policy"]


def test_verification_disabled_without_operator_configuration(monkeypatch):
    monkeypatch.delenv("TIKTOK_VERIFICATION_FILENAME", raising=False)
    monkeypatch.delenv("TIKTOK_VERIFICATION_CONTENT", raising=False)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        assert client.get("/tiktok-verification.txt").status_code == 404


def test_verification_exact_match_only(monkeypatch):
    monkeypatch.setenv("TIKTOK_VERIFICATION_FILENAME", "tiktok-check-123.txt")
    monkeypatch.setenv("TIKTOK_VERIFICATION_CONTENT", "tiktok-verification-123")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        response = client.get("/tiktok-check-123.txt")
        assert response.status_code == 200
        assert response.mimetype == "text/plain"
        assert response.data == b"tiktok-verification-123\n"
        assert response.headers["Cache-Control"] == "no-store"
        assert client.get("/tiktok-check-123.txt.bak").status_code == 404
        assert client.get("/different.txt").status_code == 404


def test_verification_rejects_invalid_configuration(monkeypatch):
    monkeypatch.setenv("TIKTOK_VERIFICATION_FILENAME", "../secret.txt")
    monkeypatch.setenv("TIKTOK_VERIFICATION_CONTENT", "tiktok-verification-123")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        assert client.get("/secret.txt").status_code == 404
    monkeypatch.setenv("TIKTOK_VERIFICATION_FILENAME", "tiktok-check.txt")
    monkeypatch.setenv("TIKTOK_VERIFICATION_CONTENT", "line1\nline2")
    with app.test_client() as client:
        assert client.get("/tiktok-check.txt").status_code == 404


def test_verification_never_serves_other_files(monkeypatch):
    monkeypatch.setenv("TIKTOK_VERIFICATION_FILENAME", "tiktok-verify.txt")
    monkeypatch.setenv("TIKTOK_VERIFICATION_CONTENT", "safe-token-123")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        for path in ("/.env", "/README.md", "/tiktok-verify.txt/", "/tiktok-verify.txt.bak"):
            assert client.get(path).status_code == 404
        response = client.get("/tiktok-verify.txt")
        assert response.status_code == 200
        assert response.data == b"safe-token-123\n"
        assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_verification_rejects_control_characters(monkeypatch):
    monkeypatch.setenv("TIKTOK_VERIFICATION_FILENAME", "verify.txt")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        for invalid in ("abc\nxyz", "abc\rxyz", "<script>", "token with spaces"):
            monkeypatch.setenv("TIKTOK_VERIFICATION_CONTENT", invalid)
            assert client.get("/verify.txt").status_code == 404
