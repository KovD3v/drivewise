from decimal import Decimal
from typing import Any

from app.schemas.advisor import (
    AdvisorListingSummary,
    AdvisorRecommendationItem,
    AdvisorRecommendationRequest,
)
from app.schemas.vehicles import VehicleSummary


def build_recommendations(
    request: AdvisorRecommendationRequest,
    candidates: list[dict[str, Any]],
) -> list[AdvisorRecommendationItem]:
    scored_items = [_score_candidate(request, candidate) for candidate in candidates]
    scored_items.sort(
        key=lambda item: (
            -item.score,
            _item_sort_price(item),
            item.vehicle.make,
            item.vehicle.model,
        )
    )
    return scored_items[:5]


def _item_sort_price(item: AdvisorRecommendationItem) -> float:
    if item.best_listing and item.best_listing.price_eur is not None:
        return item.best_listing.price_eur
    if item.vehicle.base_price_eur is not None:
        return item.vehicle.base_price_eur
    return 999999


def _score_candidate(
    request: AdvisorRecommendationRequest,
    candidate: dict[str, Any],
) -> AdvisorRecommendationItem:
    vehicle = candidate["vehicle"]
    specs = candidate.get("specs", [])
    spec = specs[0] if specs else {}
    best_listing = _choose_best_listing(request, candidate.get("listings", []), vehicle)

    price_eur = _as_float(
        best_listing.get("price_eur") if best_listing else vehicle.get("base_price_eur")
    )
    base_price_eur = _as_float(vehicle.get("base_price_eur"))
    consumption = _as_float(spec.get("consumption_l_100km"))
    wltp_range = spec.get("wltp_range_km")
    co2 = spec.get("co2_g_km")
    seats = spec.get("seats")
    cargo = _as_float(spec.get("cargo_volume_liters"))
    mileage = best_listing.get("mileage") if best_listing else None
    missing_fields: list[str] = []
    rationale_parts: list[str] = []

    score = 50.0
    if best_listing is None or best_listing.get("price_eur") is None:
        missing_fields.append("listing_price_eur")
        rationale_parts.append("Missing price data; base price was used when available.")
        score -= 4
    score += _budget_score(request, price_eur, missing_fields, rationale_parts)
    score += _mileage_score(request, mileage, best_listing, missing_fields)
    score += _primary_use_score(
        request=request,
        vehicle=vehicle,
        consumption=consumption,
        wltp_range=wltp_range,
        seats=seats,
        cargo=cargo,
        missing_fields=missing_fields,
        rationale_parts=rationale_parts,
    )
    score += _priority_score(
        request=request,
        price_eur=price_eur,
        consumption=consumption,
        wltp_range=wltp_range,
        co2=co2,
        seats=seats,
        cargo=cargo,
        missing_fields=missing_fields,
        rationale_parts=rationale_parts,
    )
    score += _preference_score(request, vehicle, rationale_parts)

    score = round(max(score, 0.0), 2)
    if missing_fields:
        rationale_parts.append("Missing data was penalized, but the vehicle was kept.")

    evidence = {
        "price_eur": price_eur,
        "base_price_eur": base_price_eur,
        "budget_min_eur": request.budget_min_eur,
        "budget_max_eur": request.budget_max_eur,
        "within_budget": price_eur is not None
        and price_eur <= request.budget_max_eur
        and (request.budget_min_eur is None or price_eur >= request.budget_min_eur),
        "mileage": mileage,
        "max_mileage": request.max_mileage,
        "consumption_l_100km": consumption,
        "wltp_range_km": wltp_range,
        "co2_g_km": co2,
        "seats": seats,
        "cargo_volume_liters": cargo,
        "body_style": vehicle.get("body_style"),
        "fuel_type": vehicle.get("fuel_type"),
        "missing_fields": missing_fields,
    }

    return AdvisorRecommendationItem(
        vehicle=VehicleSummary.model_validate(vehicle),
        best_listing=AdvisorListingSummary.model_validate(best_listing)
        if best_listing
        else None,
        score=score,
        rationale=" ".join(rationale_parts),
        evidence=evidence,
    )


def _choose_best_listing(
    request: AdvisorRecommendationRequest,
    listings: list[dict[str, Any]],
    vehicle: dict[str, Any],
) -> dict[str, Any] | None:
    if not listings:
        return None

    def listing_rank(listing: dict[str, Any]) -> tuple[float, float, int, str]:
        price = _as_float(listing.get("price_eur"))
        mileage = listing.get("mileage")
        score = _budget_fit_value(request, price)

        if request.max_mileage is not None and mileage is not None:
            if mileage <= request.max_mileage:
                score += 5
            else:
                score -= min(20, (mileage - request.max_mileage) / 5000)

        price_sort = price if price is not None else vehicle.get("base_price_eur") or 999999
        mileage_sort = mileage if mileage is not None else 999999999
        return (score, -float(price_sort), -int(mileage_sort), listing["title"])

    return max(listings, key=listing_rank)


def _budget_score(
    request: AdvisorRecommendationRequest,
    price_eur: float | None,
    missing_fields: list[str],
    rationale_parts: list[str],
) -> float:
    if price_eur is None:
        missing_fields.append("price_eur")
        rationale_parts.append("Missing price data.")
        return -10

    if price_eur > request.budget_max_eur:
        over_amount = price_eur - request.budget_max_eur
        rationale_parts.append("Price is above the requested budget.")
        return -min(70, 12 + over_amount / 40)

    if request.budget_min_eur is not None and price_eur < request.budget_min_eur:
        rationale_parts.append("Price is below the requested budget range.")
        return -4

    under_ratio = (request.budget_max_eur - price_eur) / request.budget_max_eur
    rationale_parts.append("Price fits the requested budget.")
    return 20 - min(10, under_ratio * 20)


def _mileage_score(
    request: AdvisorRecommendationRequest,
    mileage: int | None,
    best_listing: dict[str, Any] | None,
    missing_fields: list[str],
) -> float:
    if request.max_mileage is None:
        return 0
    if best_listing is None or mileage is None:
        missing_fields.append("mileage")
        return -4
    if mileage <= request.max_mileage:
        return 8
    return -min(25, 8 + ((mileage - request.max_mileage) / 5000))


def _primary_use_score(
    *,
    request: AdvisorRecommendationRequest,
    vehicle: dict[str, Any],
    consumption: float | None,
    wltp_range: int | None,
    seats: int | None,
    cargo: float | None,
    missing_fields: list[str],
    rationale_parts: list[str],
) -> float:
    body_style = vehicle.get("body_style")
    score = 0.0

    if request.primary_use in {"city", "new_driver"}:
        if body_style == "city_car":
            score += 18
            rationale_parts.append("City-car body style fits urban use.")
        elif body_style in {"hatchback", "small_hatchback"}:
            score += 10
            rationale_parts.append("Compact hatchback body style fits urban use.")
        if consumption is None:
            missing_fields.append("consumption_l_100km")
            score -= 4
        elif consumption <= 5:
            score += 12
            rationale_parts.append("Low consumption supports city use.")
        elif consumption <= 6:
            score += 6

    if request.primary_use == "family":
        if seats is None:
            missing_fields.append("seats")
            score -= 4
        elif seats >= 5:
            score += 10
            rationale_parts.append("Five seats support family use.")
        if cargo is None:
            missing_fields.append("cargo_volume_liters")
            score -= 4
        elif cargo >= 350:
            score += 16
            rationale_parts.append("Cargo volume supports family use.")
        elif cargo >= 280:
            score += 8

    if request.primary_use == "highway":
        if wltp_range is not None and wltp_range >= 450:
            score += 12
            rationale_parts.append("WLTP range supports highway use.")
        elif consumption is not None and consumption <= 5.5:
            score += 10
            rationale_parts.append("Low consumption supports highway use.")
        else:
            missing_fields.append("wltp_range_or_consumption")
            score -= 4

    if request.primary_use == "work":
        if cargo is not None and cargo >= 300:
            score += 10
            rationale_parts.append("Cargo space supports work use.")
        elif cargo is None:
            missing_fields.append("cargo_volume_liters")
            score -= 4

    return score


def _priority_score(
    *,
    request: AdvisorRecommendationRequest,
    price_eur: float | None,
    consumption: float | None,
    wltp_range: int | None,
    co2: int | None,
    seats: int | None,
    cargo: float | None,
    missing_fields: list[str],
    rationale_parts: list[str],
) -> float:
    score = 0.0
    priorities = set(request.priorities)

    if "price" in priorities and price_eur is not None:
        score += min(12, ((request.budget_max_eur - price_eur) / request.budget_max_eur) * 15)
        rationale_parts.append("Price priority rewards lower cost.")

    if "consumption" in priorities:
        if consumption is not None:
            if consumption <= 4:
                score += 16
            elif consumption <= 5:
                score += 12
            elif consumption <= 6:
                score += 7
            else:
                score -= 3
            rationale_parts.append("Consumption priority used WLTP l/100km.")
        elif co2 == 0:
            score += 10
            rationale_parts.append("Electric vehicle gets consumption credit from zero CO2.")
        else:
            missing_fields.append("consumption_l_100km")
            score -= 5

    if "space" in priorities:
        if seats is None or cargo is None:
            missing_fields.append("space_data")
            score -= 5
        else:
            score += min(14, max(0, cargo - 200) / 18)
            if seats >= 5:
                score += 4
            rationale_parts.append("Space priority used seats and cargo volume.")

    if "range" in priorities:
        if wltp_range is not None:
            score += min(14, wltp_range / 40)
            rationale_parts.append("Range priority used WLTP range.")
        elif consumption is not None:
            score += max(0, 10 - consumption)
            rationale_parts.append("Range priority used low fuel consumption proxy.")
        else:
            missing_fields.append("range_data")
            score -= 5

    if "reliability" in priorities:
        missing_fields.append("reliability_data")
        score -= 3
        rationale_parts.append("Reliability dataset is not available in the MVP.")

    if "safety" in priorities:
        missing_fields.append("safety_data")
        score -= 3
        rationale_parts.append("Safety dataset is not available in the MVP.")

    return score


def _preference_score(
    request: AdvisorRecommendationRequest,
    vehicle: dict[str, Any],
    rationale_parts: list[str],
) -> float:
    score = 0.0

    if (
        request.preferred_fuel_type
        and vehicle.get("fuel_type") == request.preferred_fuel_type
    ):
        score += 12
        rationale_parts.append("Fuel type matches the preference.")

    if (
        request.preferred_body_style
        and vehicle.get("body_style") == request.preferred_body_style
    ):
        score += 12
        rationale_parts.append("Body style matches the preference.")

    return score


def _budget_fit_value(
    request: AdvisorRecommendationRequest,
    price_eur: float | None,
) -> float:
    if price_eur is None:
        return -10
    if price_eur > request.budget_max_eur:
        return -(price_eur - request.budget_max_eur)
    if request.budget_min_eur is not None and price_eur < request.budget_min_eur:
        return 50000 - (request.budget_min_eur - price_eur)
    return 100000 - (request.budget_max_eur - price_eur)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)
