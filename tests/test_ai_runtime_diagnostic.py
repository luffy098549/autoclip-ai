"""Tests for the read-only AI runtime diagnostic."""
from scripts.check_ai_runtime import inspect_runtime, main


def test_installed_and_enabled():
    assert inspect_runtime(lambda name: object() if name == "faster_whisper" else None,
                           {"AI_ENABLED": "true"}) == (True, True)


def test_disabled_and_missing():
    assert inspect_runtime(lambda name: None, {"AI_ENABLED": "false"}) == (False, False)


def test_invalid_import_metadata_is_handled():
    def broken(_name):
        raise ValueError("missing spec")
    assert inspect_runtime(broken, {"AI_ENABLED": "yes"}) == (True, False)


def test_no_secrets_or_model_loading(monkeypatch, capsys):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "do-not-print-this")
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_runtime", lambda: (True, False))
    assert main() == 1
    output = capsys.readouterr().out
    assert "faster-whisper is missing" in output
    assert "do-not-print-this" not in output


def test_installed_runtime_is_not_claimed_model_ready(monkeypatch, capsys):
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_runtime", lambda: (True, True))
    assert main() == 0
    assert "NOT verified" in capsys.readouterr().out
