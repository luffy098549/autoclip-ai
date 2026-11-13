"""Tests for the read-only AI runtime diagnostic."""
from scripts.check_ai_runtime import inspect_runtime, inspect_media_tools, main


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
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_media_tools", lambda: (True, True))
    assert main() == 1
    output = capsys.readouterr().out
    assert "faster-whisper is missing" in output
    assert "do-not-print-this" not in output


def test_installed_runtime_is_not_claimed_model_ready(monkeypatch, capsys):
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_runtime", lambda: (True, True))
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_media_tools", lambda: (True, True))
    assert main() == 0
    assert "NOT verified" in capsys.readouterr().out


def test_invalid_ai_enabled_fails_closed(monkeypatch, capsys):
    monkeypatch.setenv("AI_ENABLED", "tru")
    monkeypatch.setenv("SECRET_KEY", "never-echo-secret")
    assert main() == 2
    output = capsys.readouterr().out
    assert "unrecognized value" in output
    assert "never-echo-secret" not in output


def test_os_error_during_dependency_lookup_is_handled():
    def broken(_name):
        raise OSError("package metadata inaccessible")
    assert inspect_runtime(broken, {"AI_ENABLED": "true"}) == (True, False)


def test_media_tools_report_each_binary_independently():
    assert inspect_media_tools(lambda name: "/usr/bin/" + name if name == "ffmpeg" else None) == (True, False)
    assert inspect_media_tools(lambda name: None) == (False, False)


def test_enabled_ai_requires_both_media_tools(monkeypatch, capsys):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_runtime", lambda: (True, True))
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_media_tools", lambda: (True, False))
    assert main() == 1
    assert "FFmpeg and FFprobe" in capsys.readouterr().out


def test_disabled_ai_reports_missing_tools_without_failure(monkeypatch, capsys):
    monkeypatch.setenv("AI_ENABLED", "false")
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_runtime", lambda: (False, False))
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_media_tools", lambda: (False, False))
    assert main() == 0
    assert "FFprobe installed: no" in capsys.readouterr().out


def test_enabled_ai_missing_both_dependencies_reports_media_failure(monkeypatch, capsys):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_runtime", lambda: (True, False))
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_media_tools", lambda: (False, False))
    assert main() == 1
    output = capsys.readouterr().out
    assert "FFmpeg and FFprobe" in output
    assert "faster-whisper installed: no" in output


def test_enabled_ai_missing_whisper_with_media_available(monkeypatch, capsys):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_runtime", lambda: (True, False))
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_media_tools", lambda: (True, True))
    assert main() == 1
    assert "faster-whisper is missing" in capsys.readouterr().out


def test_media_lookup_os_error_isolated_per_binary():
    def lookup(binary):
        if binary == "ffmpeg":
            raise OSError("unavailable")
        return "/usr/bin/ffprobe"
    assert inspect_media_tools(lookup) == (False, True)


def test_media_lookup_invalid_type_is_handled():
    def lookup(_binary):
        raise TypeError("invalid path")
    assert inspect_media_tools(lookup) == (False, False)


def test_nonstring_ai_enabled_does_not_crash(monkeypatch, capsys):
    class WeirdEnvironment(dict):
        def get(self, key, default=None):
            if key == "AI_ENABLED":
                return 42
            return super().get(key, default)
    monkeypatch.setattr("scripts.check_ai_runtime.os.environ", WeirdEnvironment())
    assert main() == 2
    assert "unrecognized value" in capsys.readouterr().out


def test_enabled_ai_reports_all_missing_dependencies(monkeypatch, capsys):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_runtime", lambda: (True, False))
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_media_tools", lambda: (False, False))
    assert main() == 1
    output = capsys.readouterr().out
    assert "FFmpeg and FFprobe executables" in output
    assert "faster-whisper is missing" in output


def test_enabled_ai_missing_media_but_whisper_present(monkeypatch, capsys):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_runtime", lambda: (True, True))
    monkeypatch.setattr("scripts.check_ai_runtime.inspect_media_tools", lambda: (False, True))
    assert main() == 1
    output = capsys.readouterr().out
    assert "FFmpeg and FFprobe executables" in output
    assert "faster-whisper is missing" not in output
