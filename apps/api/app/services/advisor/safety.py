"""Source-backed safety assessment."""

from collections.abc import Mapping
from typing import Any

from app.services.advisor.decision import ModuleAssessment

SAFETY_VERSION = "safety-v1"
_PERCENT_FIELDS = (
    "adult_occupant_percent",
    "child_occupant_percent",
    "vulnerable_road_users_percent",
    "safety_assist_percent",
)


def assess_safety(candidate: dict[str, Any]) -> ModuleAssessment:
    ratings = ((candidate.get("decision_context") or {}).get("safety") or {}).get(
        "ratings", []
    )
    values = [
        float(value)
        for rating in ratings
        for field in _PERCENT_FIELDS
        if (value := _get(rating, field)) is not None
    ]
    if values:
        return ModuleAssessment(
            status="available", version=SAFETY_VERSION, value=sum(values) / len(values),
            details={"method": "available_rating_percentages"},
            evidence=tuple(dict(rating) for rating in ratings),
        )
    stars = [float(_get(rating, "overall_stars")) for rating in ratings if _get(rating, "overall_stars") is not None]
    if stars:
        return ModuleAssessment(
            status="available", version=SAFETY_VERSION,
            value=sum(stars) / len(stars) / 5 * 100,
            details={"method": "overall_stars"},
            evidence=tuple(dict(rating) for rating in ratings),
        )
    return ModuleAssessment(status="insufficient_data", version=SAFETY_VERSION, missing_data=("safety_ratings",))


def _get(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, Mapping) else getattr(value, key, None)
