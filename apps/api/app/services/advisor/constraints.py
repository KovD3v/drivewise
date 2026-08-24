from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.garage import garage_fit


ConstraintStatus = Literal["eligible", "excluded", "insufficient_data"]


@dataclass(frozen=True)
class ConstraintEvaluation:
    status: ConstraintStatus
    reasons: tuple[str, ...] = ()
    missing_data: tuple[str, ...] = ()
    soft_tradeoffs: tuple[str, ...] = ()


def evaluate_constraints(
    request: AdvisorRecommendationRequest, candidate: dict[str, Any]
) -> ConstraintEvaluation:
    spec = candidate.get("spec") or {}
    offer = candidate.get("offer") or {}
    reasons: list[str] = []
    missing: list[str] = []
    tradeoffs: list[str] = []

    if request.condition != "any":
        condition = "new" if offer.get("condition") == "new" else "used"
        if condition != request.condition:
            reasons.append("condition_mismatch")
    price = _number(offer.get("price_eur"))
    if price is None:
        missing.append("offer.price_eur")
    elif request.budget_min_eur is not None and price < request.budget_min_eur:
        reasons.append("below_budget_min")
    elif request.constraint_modes.budget == "hard" and price > request.budget_max_eur:
        reasons.append("above_budget")
    elif price > request.budget_max_eur * 1.1:
        reasons.append("above_budget_tolerance")

    mileage = _number(offer.get("mileage"))
    if request.max_mileage is not None:
        if mileage is None:
            missing.append("offer.mileage")
        elif mileage > request.max_mileage:
            reasons.append("above_max_mileage")

    seats = _number(spec.get("seats"))
    if request.passengers_usual is not None:
        if seats is None:
            missing.append("vehicle.seats")
        elif seats < request.passengers_usual:
            reasons.append("insufficient_seats")

    body = spec.get("body_style")
    if request.preferred_body_style is not None and body != request.preferred_body_style:
        if request.constraint_modes.body_style == "hard":
            reasons.append("body_style_mismatch")
        else:
            tradeoffs.append("body_style_mismatch")
    fuel = spec.get("fuel_type")
    if request.preferred_fuel_type is not None and fuel != request.preferred_fuel_type:
        if request.constraint_modes.fuel_type == "hard":
            reasons.append("fuel_type_mismatch")
        else:
            tradeoffs.append("fuel_type_mismatch")
    transmission = (candidate.get("decision_context") or {}).get("powertrain", {}).get(
        "transmission_type", spec.get("transmission")
    )
    if request.automatic_required and transmission is None:
        missing.append("vehicle.transmission")
    elif request.automatic_required and str(transmission).lower() not in {"automatic", "auto"}:
        if request.constraint_modes.transmission == "hard":
            reasons.append("transmission_mismatch")
        else:
            tradeoffs.append("transmission_mismatch")

    if request.garage:
        garage = garage_fit(request, candidate)
        if garage.status == "insufficient_data":
            if request.constraint_modes.garage == "hard":
                missing.extend(garage.missing_data)
            else:
                tradeoffs.append("garage_insufficient_data")
        elif garage.value == 0:
            if request.constraint_modes.garage == "hard":
                reasons.append("garage_incompatible")
            else:
                tradeoffs.append("garage_incompatible")

    if reasons:
        status: ConstraintStatus = "excluded"
    elif missing:
        status = "insufficient_data"
    else:
        status = "eligible"
    return ConstraintEvaluation(status, tuple(reasons), tuple(dict.fromkeys(missing)), tuple(tradeoffs))


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None
