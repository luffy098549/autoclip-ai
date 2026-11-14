"""Rights assessment gate for content processed by AutoClip AI."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    reason: str


_PLACEHOLDERS = frozenset({"n/a", "na", "none", "null", "unknown", "tbd"})


def _has_meaningful_evidence(evidence: object) -> bool:
    """Check supplied metadata only; this is not independent license verification."""
    return (
        isinstance(evidence, str)
        and any(character.isalnum() for character in evidence)
        and evidence.strip().casefold() not in _PLACEHOLDERS
    )


def assess_rights(status: str, evidence: str | None = None) -> RightsDecision:
    """Deny malformed statuses and evidence without raising on untrusted values."""
    if not isinstance(status, str) or status not in {"licensed", "owned", "denied", "unverified"}:
        return RightsDecision(False, "Unknown rights status")
    if status in {"owned", "licensed"} and _has_meaningful_evidence(evidence):
        return RightsDecision(True, "Rights evidence supplied")
    return RightsDecision(False, "Valid permission evidence required before processing")
