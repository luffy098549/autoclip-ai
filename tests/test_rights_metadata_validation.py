"""Regression tests for malformed or unverified rights metadata."""
import pytest

from app.services.rights import assess_rights


@pytest.mark.parametrize("status", [None, 0, False, [], {}, ["owned"], "OWNED", "unknown"])
def test_malformed_status_fails_closed(status):
    decision = assess_rights(status, "creator permission")
    assert not decision.allowed
    assert decision.reason == "Unknown rights status"


@pytest.mark.parametrize("status", ["owned", "licensed"])
@pytest.mark.parametrize("evidence", [None, "", " \t\n ", 42, True, [], {}, b"permission",
                                      "\u200b", "\u200d", "\ufeff", "🔒", "—",
                                      "N/A", "n/a", "none", "NULL", "unknown", "TBD"])
def test_malformed_or_placeholder_evidence_fails_closed(status, evidence):
    assert not assess_rights(status, evidence).allowed


@pytest.mark.parametrize("status", ["owned", "licensed"])
@pytest.mark.parametrize("evidence", ["original recording", "license agreement #123",
                                      "© creator 2026", "https://example.org/license/123"])
def test_substantive_metadata_passes_gate(status, evidence):
    assert assess_rights(status, evidence).allowed


@pytest.mark.parametrize("status", ["denied", "unverified"])
def test_negative_status_cannot_be_overridden(status):
    assert not assess_rights(status, "creator permission").allowed
