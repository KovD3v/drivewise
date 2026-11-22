from __future__ import annotations

from app.services.advisor.decision import ModuleAssessment


CONFIDENCE_VERSION = "decision-confidence-v1"


def decision_confidence(
    *,
    profile_completeness: float,
    evidence_completeness: float,
    ranking_stability: float,
) -> ModuleAssessment:
    value = profile_completeness * 0.45 + evidence_completeness * 0.35 + ranking_stability * 0.20
    components = {
        "profile_completeness": profile_completeness,
        "evidence_completeness": evidence_completeness,
        "ranking_stability": ranking_stability,
    }
    return ModuleAssessment(
        status="available",
        version=CONFIDENCE_VERSION,
        value=round(_bounded(value), 1),
        details=components,
    )


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, float(value)))
