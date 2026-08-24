"""Adapter for calibrated Vehicle DNA specialist assessments."""

from collections.abc import Mapping
from typing import Any

from app.services.advisor.decision import ModuleAssessment

DNA_VERSION = "vehicle-dna-v1"
_FACTORS = ("comfort", "sport", "travel", "technology")


def assess_vehicle_dna(candidate: dict[str, Any]) -> dict[str, ModuleAssessment]:
    context = candidate.get("decision_context") or {}
    supplied = context.get("vehicle_dna")
    if not isinstance(supplied, Mapping):
        return {factor: _missing() for factor in _FACTORS}
    feature_evidence = tuple(supplied.get("features") or ())
    result: dict[str, ModuleAssessment] = {}
    for factor in _FACTORS:
        value = supplied.get(factor)
        if isinstance(value, Mapping) and value.get("value") is not None:
            result[factor] = ModuleAssessment(
                status="available", version=str(value.get("version", DNA_VERSION)),
                value=max(0.0, min(100.0, float(value["value"]))),
                details=dict(value.get("details") or {}),
                evidence=tuple(value.get("evidence") or ()),
            )
        else:
            result[factor] = _missing(feature_evidence)
    return result


def _missing(evidence: tuple[Any, ...] = ()) -> ModuleAssessment:
    return ModuleAssessment(
        status="insufficient_data", version=DNA_VERSION,
        details={"features": len(evidence)} if evidence else {},
        evidence=evidence,
        missing_data=("vehicle_dna_assessment",),
    )
