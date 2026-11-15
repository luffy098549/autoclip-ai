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
