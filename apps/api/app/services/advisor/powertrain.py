"""Deterministic powertrain fit assessment for Advisor v3."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.decision import ModuleAssessment
from app.services.advisor.energy_prices import (
    ELECTRICITY_PRICE_EUR_PER_KWH,
    LIQUID_ENERGY_PRICES_EUR_PER_LITER,
)


POWERTRAIN_FIT_VERSION = "powertrain-fit-v1"
CITY_ANNUAL_KM_THRESHOLD = 15_000
HIGH_DISTANCE_ANNUAL_KM_THRESHOLD = 25_000
LONG_DISTANCE_ANNUAL_KM_THRESHOLD = 30_000
DIESEL_HIGHWAY_ANNUAL_KM_THRESHOLD = 22_000
EV_HIGHWAY_RANGE_THRESHOLD_KM = 250

_LIQUID_TYPES = frozenset(LIQUID_ENERGY_PRICES_EUR_PER_LITER)
_HYBRID_TYPES = frozenset(
    {"mild_hybrid_petrol", "full_hybrid_petrol", "hybrid_petrol"}
)


def powertrain_fit(
    request: AdvisorRecommendationRequest | Mapping[str, Any],
    candidate: dict[str, Any],
) -> ModuleAssessment:
    spec = candidate.get("spec") or {}
    fuel_type = spec.get("fuel_type")
    annual_km = _value(request, "annual_km")
    usage = _value(request, "usage") or [_value(request, "primary_use")]
    usage = {str(value) for value in usage if value}
    missing: list[str] = []

    if fuel_type not in _LIQUID_TYPES and fuel_type != "electric":
        missing.append("vehicle.fuel_type")
    if not usage:
        missing.append("request.usage")
    if _positive(annual_km) is None:
        missing.append("request.annual_km")

    if fuel_type == "electric":
        if _positive(spec.get("energy_consumption_kwh_100km")) is None:
            missing.append("vehicle.energy_consumption_kwh_100km")
        if _positive(spec.get("wltp_range_km")) is None:
            missing.append("vehicle.wltp_range_km")
    elif fuel_type in _LIQUID_TYPES and _positive(spec.get("consumption_l_100km")) is None:
        missing.append("vehicle.consumption_l_100km")

    if fuel_type == "plug_in_hybrid_petrol":
        # PHEV is intentionally recognized, but cannot be assessed without a
        # charging arrangement because its useful electric share depends on it.
        if _positive(spec.get("energy_consumption_kwh_100km")) is None:
            missing.append("vehicle.energy_consumption_kwh_100km")
        if _positive(spec.get("wltp_range_km")) is None:
            missing.append("vehicle.wltp_range_km")
        if not _charging_context(candidate):
            missing.append("charging_context")

    if missing:
        return ModuleAssessment(
            status="insufficient_data",
            version=POWERTRAIN_FIT_VERSION,
            details={"fuel_type": fuel_type},
            missing_data=tuple(dict.fromkeys(missing)),
        )

    km = float(annual_km)
    score = _base_score(str(fuel_type), usage, km)
    if fuel_type == "electric" and "highway" in usage:
        score += max(-6.0, min(0.0, (float(spec["wltp_range_km"]) - 350) / 100))
    if fuel_type == "plug_in_hybrid_petrol" and "highway" in usage:
        score -= 4

    energy_rate = (
        ELECTRICITY_PRICE_EUR_PER_KWH
        if fuel_type == "electric"
        else LIQUID_ENERGY_PRICES_EUR_PER_LITER[str(fuel_type)]
    )
    return ModuleAssessment(
        status="available",
        version=POWERTRAIN_FIT_VERSION,
        value=max(0.0, min(100.0, score)),
        details={
            "fuel_type": fuel_type,
            "annual_km": km,
            "usage": sorted(usage),
            "energy_rate": energy_rate,
            "ev_highway_range_threshold_km": EV_HIGHWAY_RANGE_THRESHOLD_KM,
        },
        assumptions=(
            "powertrain-fit-v1 uses deterministic city/highway and annual-distance thresholds.",
            "EV highway range affects fit continuously; it is not a hard exclusion.",
        ),
        evidence=(
            {"metric": "fuel_type", "value": fuel_type},
            {"metric": "annual_km", "value": km},
        ),
    )


def _base_score(fuel_type: str, usage: set[str], annual_km: float) -> float:
    if fuel_type == "electric":
        score = 82.0
        if annual_km > LONG_DISTANCE_ANNUAL_KM_THRESHOLD:
            score += 4
        if "city" in usage:
            score += 6
        if "highway" in usage:
            score -= 6
        return score
    if fuel_type in _HYBRID_TYPES:
        score = 86.0
        if "city" in usage:
            score += 5
        if annual_km > LONG_DISTANCE_ANNUAL_KM_THRESHOLD and "highway" in usage:
            score -= 4
        return score
    if fuel_type == "plug_in_hybrid_petrol":
        return 84.0 + (6 if "city" in usage else 0)
    if fuel_type == "diesel":
        score = 78.0
        if annual_km >= DIESEL_HIGHWAY_ANNUAL_KM_THRESHOLD:
            score += 8
        if "highway" in usage:
            score += 7
        if "city" in usage and annual_km < 18_000:
            score -= 12
        return score
    score = 78.0
    if annual_km < CITY_ANNUAL_KM_THRESHOLD:
        score += 7
    if annual_km > HIGH_DISTANCE_ANNUAL_KM_THRESHOLD:
        score -= 8
    return score


def _charging_context(candidate: Mapping[str, Any]) -> bool:
    context = candidate.get("charging_context")
    if context is None:
        decision_context = candidate.get("decision_context") or {}
        context = decision_context.get("charging_context")
        if context is None:
            context = (decision_context.get("powertrain") or {}).get(
                "charging_context"
            )
    if context is None:
        context = (candidate.get("spec") or {}).get("charging_context")
    if isinstance(context, Mapping):
        return any(bool(value) for value in context.values())
    return bool(context)


def _value(obj: Any, name: str) -> Any:
    return getattr(obj, name, None) if not isinstance(obj, Mapping) else obj.get(name)


def _positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
