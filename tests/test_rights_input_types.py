"""Fail-closed tests for untrusted rights metadata."""

import pytest

from app.services.rights import assess_rights


@pytest.mark.parametrize("status", [None, 0, False, [], {}, ["owned"], "OWNED", "unknown"])
def test_invalid_status_is_denied_without_exception(status):
    decision = assess_rights(status, "creator permission")
    assert not decision.allowed
    assert decision.reason == "Unknown rights status"


@pytest.mark.parametrize("evidence", [None, "", " \t\n ", 42, True, [], {}, ["permission"]])
@pytest.mark.parametrize("status", ["owned", "licensed"])
def test_invalid_evidence_is_denied_without_exception(status, evidence):
    decision = assess_rights(status, evidence)
    assert not decision.allowed
    assert decision.reason == "Valid permission evidence required before processing"


@pytest.mark.parametrize("evidence", ["\u200b", "\u200d", "\ufeff", "🔒", "—", "N/A", "n/a", "none", "NULL", "unknown", "TBD"])
@pytest.mark.parametrize("status", ["owned", "licensed"])
def test_invisible_or_placeholder_evidence_is_denied(status, evidence):
    assert not assess_rights(status, evidence).allowed


@pytest.mark.parametrize("evidence", ["  original recording  ", "license agreement #123", "© creator 2026", "https://example.org/license/123"])
@pytest.mark.parametrize("status", ["owned", "licensed"])
def test_substantive_evidence_is_accepted(status, evidence):
    assert assess_rights(status, evidence).allowed


@pytest.mark.parametrize("status", ["denied", "unverified"])
def test_negative_status_never_overridden_by_evidence(status):
    assert not assess_rights(status, "creator permission").allowed
