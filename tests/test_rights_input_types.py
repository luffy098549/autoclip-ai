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


@pytest.mark.parametrize("status", ["owned", "licensed"])
def test_supported_status_with_nonempty_evidence_is_allowed(status):
    assert assess_rights(status, "  original recording  ").allowed


@pytest.mark.parametrize("status", ["denied", "unverified"])
def test_negative_status_never_overridden_by_evidence(status):
    assert not assess_rights(status, "creator permission").allowed
