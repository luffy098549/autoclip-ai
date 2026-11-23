"""Fail-closed public deployment configuration checks."""
import pytest

from app import create_app


def _config():
    return {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}


def test_public_deployment_rejects_missing_secret(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEPLOYMENT", "true")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    with pytest.raises(RuntimeError, match="stable SECRET_KEY"):
        create_app(_config())


def test_public_deployment_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setenv("SECRET_KEY", "short")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    with pytest.raises(RuntimeError, match="stable SECRET_KEY"):
        create_app(_config())


def test_public_deployment_rejects_insecure_cookies(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setenv("SECRET_KEY", "a" * 48)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE"):
        create_app(_config())


def test_public_deployment_accepts_explicit_secure_configuration(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setenv("SECRET_KEY", "b" * 48)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    app = create_app(_config())
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SECRET_KEY"] == "b" * 48


def test_local_development_keeps_existing_defaults(monkeypatch):
    monkeypatch.delenv("PUBLIC_DEPLOYMENT", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    app = create_app(_config())
    assert app.config["SECRET_KEY"]
    assert app.config["SESSION_COOKIE_SECURE"] is False
