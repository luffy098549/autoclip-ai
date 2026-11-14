"""Rights assessment gate for content processed by AutoClip AI."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    reason: str


def _has_meaningful_evidence(evidence: object) -> bool:
    """Require visible, substantive text rather than invisible control characters."""
    return (
        isinstance(evidence, str)
        and any(character.isalnum() for character in evidence)
        and evidence.strip().casefold() not in {"n/a", "na", "none", "null", "unknown", "tbd"}
    )


def assess_rights(status: str, evidence: str | None = None) -> RightsDecision:
    """Fail closed for malformed or unsupported rights metadata."""
    if not isinstance(status, str) or status not in {"licensed", "owned", "denied", "unverified"}:
        return RightsDecision(False, "Unknown rights status")
    if status in {"owned", "licensed"} and _has_meaningful_evidence(evidence):
        return RightsDecision(True, "Rights evidence supplied")
    return RightsDecision(False, "Valid permission evidence required before processing")
