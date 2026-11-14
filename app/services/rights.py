"""Rights assessment gate for content processed by AutoClip AI."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    reason: str


def assess_rights(status: str, evidence: str | None = None) -> RightsDecision:
    if not isinstance(status, str) or status not in {"licensed", "owned", "denied", "unverified"}:
        return RightsDecision(False, "Unknown rights status")
    if status in {"owned", "licensed"} and isinstance(evidence, str) and evidence.strip():
        return RightsDecision(True, "Rights evidence supplied")
    return RightsDecision(False, "Valid permission evidence required before processing")
