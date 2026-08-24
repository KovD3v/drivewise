"""Applicability-first known issue penalty."""

from collections.abc import Mapping, Sequence
from typing import Any

from app.services.advisor.decision import ModuleAssessment

ISSUES_VERSION = "known-issues-v1"
_FIELDS = {
    "generation": "generation_name", "generation_name": "generation_name",
    "spec": "variant_key", "variant_key": "variant_key", "engine": "engine_code",
    "engine_code": "engine_code", "transmission": "transmission_type",
    "transmission_type": "transmission_type", "production_year": "model_year",
    "model_year": "model_year",
}


def known_issue_penalty(candidate: dict[str, Any], issues: Sequence[Any]) -> ModuleAssessment:
    if not issues:
        return ModuleAssessment(status="insufficient_data", version=ISSUES_VERSION, missing_data=("known_issues",))
    matched = 0.0
    unknown = False
    evidence = []
    for issue in issues:
        state = _applicability(candidate, issue)
        if state == "unknown":
            unknown = True
        elif state == "match":
            matched += _severity(issue)
            evidence.append(dict(issue) if isinstance(issue, Mapping) else {"issue": issue})
    missing = ("issue_applicability",) if unknown else ()
    return ModuleAssessment(status="available", version=ISSUES_VERSION, value=min(8.0, matched), evidence=tuple(evidence), missing_data=missing)


def _applicability(candidate: dict[str, Any], issue: Any) -> str:
    context = candidate.get("decision_context") or {}
    identity = context.get("identity") or {}
    powertrain = context.get("powertrain") or {}
    vehicle = candidate.get("vehicle") or {}
    spec = candidate.get("spec") or {}
    actual = {**identity, **powertrain, **vehicle, **spec}
    constraints = [(key, value) for key, value in _items(issue) if key in _FIELDS and value is not None]
    if not constraints:
        return "unknown"
    missing = False
    for key, expected in constraints:
        value = actual.get(_FIELDS[key])
        if value is None:
            missing = True
        elif str(value).lower() != str(expected).lower():
            return "conflict"
    return "unknown" if missing else "match"


def _severity(issue: Any) -> float:
    value = _get(issue, "penalty")
    if value is not None:
        return max(0.0, float(value))
    return {"low": 1.0, "moderate": 3.0, "medium": 3.0, "high": 5.0, "critical": 8.0}.get(str(_get(issue, "severity") or "moderate").lower(), 3.0)


def _items(value: Any):
    return value.items() if isinstance(value, Mapping) else vars(value).items()


def _get(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, Mapping) else getattr(value, key, None)
