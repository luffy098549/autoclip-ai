"""Rights assessment gate for content processed by AutoClip AI."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    reason: str


def assess_rights(status: str, evidence: str | None = None) -> RightsDecision:
    if status not in {"licensed", "owned", "denied", "unverified"}:
        return RightsDecision(False, "Unknown rights status")
    if status in {"owned", "licensed"} and evidence and evidence.strip():
        return RightsDecision(True, "Rights evidence supplied")
    return RightsDecision(False, "Valid permission evidence required before processing")
