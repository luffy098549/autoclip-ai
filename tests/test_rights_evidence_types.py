"""Malformed or missing rights evidence must never permit processing."""
import pytest

from app.services.rights import assess_rights


@pytest.mark.parametrize("status", ["owned", "licensed"])
@pytest.mark.parametrize("evidence", ["my own recording", "license agreement"])
def test_explicit_rights_evidence_allows(status, evidence):
    assert assess_rights(status, evidence).allowed


@pytest.mark.parametrize("status", [
    "owned", "licensed", "denied", "unverified", None, {}, [], 1, True, "OWNED", "",
])
@pytest.mark.parametrize("evidence", [None, "", "  ", 0, 42, True, [], {}, b"permission"])
def test_missing_or_malformed_rights_never_bypasses_gate(status, evidence):
    expected = (
        isinstance(status, str)
        and status in {"owned", "licensed"}
        and isinstance(evidence, str)
        and bool(evidence.strip())
    )
    assert assess_rights(status, evidence).allowed is expected
