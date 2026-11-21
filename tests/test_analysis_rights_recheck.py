"""Recheck authorization after expensive analysis before persisting results."""
from types import SimpleNamespace

import pytest

from app.services import analyzer


@pytest.mark.parametrize("allowed", [True, False])
def test_analysis_reloads_rights_before_commit(monkeypatch, allowed):
    source = SimpleNamespace(rights_status="authorized", permission_evidence="initial")
    expired = []

    def expire(obj, fields):
        expired.append((obj, fields))
        # Simulate a concurrent operator revoking permission during transcription.
        obj.rights_status = "authorized" if allowed else "revoked"
        obj.permission_evidence = "current" if allowed else None

    observed = []

    def assess(status, evidence):
        observed.append((status, evidence))
        return SimpleNamespace(allowed=allowed)

    monkeypatch.setattr(analyzer.db.session, "expire", expire)
    monkeypatch.setattr(analyzer, "assess_rights", assess)
    if allowed:
        analyzer._assert_source_rights_current(source)
    else:
        with pytest.raises(PermissionError, match="revoked"):
            analyzer._assert_source_rights_current(source)
    assert expired == [(source, ["rights_status", "permission_evidence"])]
    assert observed == [(source.rights_status, source.permission_evidence)]
