"""Narrow adapter for the future reliability specialist."""

from collections.abc import Mapping
from typing import Any

from app.services.advisor.decision import ModuleAssessment

RELIABILITY_VERSION = "reliability-v1"


def assess_reliability(candidate: dict[str, Any]) -> ModuleAssessment:
    assessment = (candidate.get("decision_context") or {}).get("reliability_assessment")
    if not isinstance(assessment, Mapping) or assessment.get("value") is None:
        return ModuleAssessment(status="insufficient_data", version=RELIABILITY_VERSION, missing_data=("reliability_assessment",))
    return ModuleAssessment(
        status="available", version=str(assessment.get("version", RELIABILITY_VERSION)),
        value=max(0.0, min(100.0, float(assessment["value"]))),
        details=dict(assessment.get("details") or {}),
        evidence=tuple(assessment.get("evidence") or ()),
        missing_data=tuple(assessment.get("missing_data") or ()),
    )
