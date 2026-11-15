"""Model configuration must be validated before database or AI access."""
from types import SimpleNamespace

import pytest

from app.services import analyzer


@pytest.mark.parametrize("invalid", [
    None, False, True, 0, 1, [], {}, b"small", "", " ", "\x00small",
    "small\nlarge", "small\tlarge", "x" * 129,
])
def test_invalid_model_identifier_rejected_before_database(monkeypatch, invalid):
    def forbidden(*args, **kwargs):
        raise AssertionError("Database must not be accessed for malformed model identifiers")

    monkeypatch.setattr(analyzer, "db", SimpleNamespace(session=SimpleNamespace(get=forbidden)))
    with pytest.raises(ValueError, match="Invalid transcription model size"):
        analyzer.analyze_source(1, model_size=invalid)


@pytest.mark.parametrize("valid", ["small", "tiny", "large-v3", "custom/model", "x" * 128])
def test_valid_model_identifier_reaches_source_lookup(monkeypatch, valid):
    calls = []

    def missing_source(model, source_id):
        calls.append(source_id)
        return None

    monkeypatch.setattr(analyzer, "db", SimpleNamespace(session=SimpleNamespace(get=missing_source)))
    with pytest.raises(ValueError, match="Source does not exist"):
        analyzer.analyze_source(1, model_size=valid)
    assert calls == [1]
