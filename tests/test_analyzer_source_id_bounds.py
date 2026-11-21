"""Source identifiers must be valid before database access or media processing."""
import pytest

from app.services import analyzer


@pytest.mark.parametrize("source_id", [
    None, True, False, 0, -1, 1.0, "1", [], {},
    2**63, 10**100,
])
def test_analyze_source_rejects_invalid_identifier_before_database(monkeypatch, source_id):
    def unexpected_database_access(*args, **kwargs):
        pytest.fail("Invalid source ID reached the database")

    monkeypatch.setattr(analyzer.db.session, "get", unexpected_database_access)
    with pytest.raises(ValueError, match="BIGINT"):
        analyzer.analyze_source(source_id)


@pytest.mark.parametrize("source_id", [1, 2**63 - 1])
def test_analyze_source_accepts_bigint_boundaries_for_lookup(monkeypatch, source_id):
    seen = []

    def missing_source(model, identifier):
        seen.append((model, identifier))
        return None

    monkeypatch.setattr(analyzer.db.session, "get", missing_source)
    with pytest.raises(ValueError, match="Source does not exist"):
        analyzer.analyze_source(source_id)
    assert seen == [(analyzer.MediaSource, source_id)]
