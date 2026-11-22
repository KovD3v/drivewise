from datetime import datetime, timezone
from decimal import Decimal
from statistics import mean
from typing import Any
from uuid import UUID

from app.schemas.advisor import (
    ModelAnalysisCostSummary,
    ModelAnalysisRequest,
    ModelAnalysisResponse,
)
from app.schemas.vehicles import (
    VehicleResolveResponse,
    VehicleSpec,
    VehicleSummary,
)
from app.services.advisor.energy_prices import (
    DEFAULT_FUEL_PRICE_EUR_PER_LITER,
    ELECTRICITY_PRICE_EUR_PER_KWH,
    flat_rate_assumption_sentence,
)


def _resolve_analysis_year(as_of: datetime | None) -> int:
    """Derive the analysis year from the current date (or an injected anchor).

    Kept injectable so tests stay deterministic: pass `as_of` explicitly to
    pin the year instead of relying on the real clock.
    """
    return (as_of or datetime.now(timezone.utc)).year


def build_model_analysis(
    request: ModelAnalysisRequest,
    candidates: list[dict[str, Any]],
    resolve_response: VehicleResolveResponse | None = None,
    *,
    as_of: datetime | None = None,
) -> ModelAnalysisResponse:
    analysis_year = _resolve_analysis_year(as_of)
    assumptions = [
        "No live market sources are used in Model Analysis V1.",
        "Reference price uses available MVP listing prices, then base price fallback.",
        "Annual kilometres are estimated deterministically from usage_profile.",
        flat_rate_assumption_sentence(),
        "Maintenance is a heuristic based on body style, powertrain, age, and mileage.",
        "Three-year depreciation is estimated at 28% of the available price.",
    ]
    warnings: list[str] = []
    missing_data: list[str] = []
    scopes = set(request.analysis_scope)
    include_price = bool(scopes & {"price", "tco"})
    include_maintenance = bool(scopes & {"maintenance", "tco"})
    include_red_flags = "red_flags" in scopes
    include_tco = "tco" in scopes
    required_inputs: set[str] = set()
    if include_price or include_red_flags:
        required_inputs.add("asking_price_eur")
    if include_maintenance or include_red_flags:
        required_inputs.add("current_km")
    resolution_confidence = 0.9

    vehicle_id = request.vehicle_id
    spec_id = request.spec_id
    if vehicle_id is None:
        if resolve_response is None or not resolve_response.matches:
            return _needs_vehicle_response(
                assumptions=assumptions,
                warnings=["vehicle_resolution_no_match"],
            )

        first_match = resolve_response.matches[0]
        vehicle_id = first_match.vehicle.id
        if first_match.spec is not None:
            spec_id = first_match.spec.id
        resolution_confidence = first_match.confidence

        if resolve_response.status == "ambiguous":
            warnings.append("vehicle_resolution_ambiguous")
            resolution_confidence = min(resolution_confidence, 0.68)

    candidate = _find_candidate(candidates, vehicle_id)
    if candidate is None:
        return _needs_vehicle_response(
            assumptions=assumptions,
            warnings=["resolved_vehicle_not_found"],
        )

    vehicle = VehicleSummary.model_validate(candidate["vehicle"])
    spec = _select_spec(candidate.get("specs", []), spec_id)
    if spec is None:
        warning = "requested_spec_not_found" if spec_id else "resolved_spec_missing"
        warnings.append(warning)
        missing_data.append("resolved_spec")

    reference_price = _market_reference_price(candidate, vehicle, spec)
    price_assessment, price_warnings, price_flags = (
        _assess_price(
            asking_price=request.asking_price_eur,
            reference_price=reference_price,
        )
        if include_price or include_red_flags
        else ("unknown", [], [])
    )
    warnings.extend(price_warnings)
    red_flags = list(price_flags) if include_red_flags else []

    if "asking_price_eur" in required_inputs and request.asking_price_eur is None:
        missing_data.append("asking_price_eur")
    if "current_km" in required_inputs and request.current_km is None:
        missing_data.append("current_km")
    elif (
        include_red_flags
        and request.current_km is not None
        and _is_high_mileage(
            vehicle.model_year,
            request.current_km,
            request.usage_profile,
            analysis_year,
        )
    ):
        red_flags.append("high_mileage_for_age")

    estimated_costs = _estimate_costs(
        request=request,
        vehicle=vehicle,
        spec=spec,
        reference_price=reference_price,
        missing_data=missing_data,
        include_price=include_price,
        include_maintenance=include_maintenance,
        include_tco=include_tco,
        analysis_year=analysis_year,
    )
    checklist = _build_checklist(vehicle, spec, red_flags)
    verdict = _build_verdict(
        missing_data,
        required_inputs,
        price_assessment,
        red_flags,
    )
    confidence = _confidence(
        resolution_confidence=resolution_confidence,
        missing_data=missing_data,
        warnings=warnings,
    )
    status = _status(
        confidence=confidence,
        missing_data=missing_data,
        warnings=warnings,
        required_inputs=required_inputs,
    )

    return ModelAnalysisResponse(
        status=status,
        resolved_vehicle=vehicle,
        resolved_spec=spec,
        verdict=verdict,
        price_assessment=price_assessment,
        estimated_costs=estimated_costs,
        red_flags=red_flags,
        checklist=checklist,
        confidence=confidence,
        assumptions=assumptions,
        warnings=warnings,
        missing_data=missing_data,
        next_actions=_next_actions(status, red_flags),
    )


def _needs_vehicle_response(
    *,
    assumptions: list[str],
    warnings: list[str],
) -> ModelAnalysisResponse:
    return ModelAnalysisResponse(
        status="needs_input",
        resolved_vehicle=None,
        resolved_spec=None,
        verdict="not_enough_data",
        price_assessment="unknown",
        estimated_costs=ModelAnalysisCostSummary(),
        red_flags=[],
        checklist=[],
        confidence=0.0,
        assumptions=assumptions,
        warnings=warnings,
        missing_data=["resolved_vehicle"],
        next_actions=["modify_parameters"],
    )


def _find_candidate(
    candidates: list[dict[str, Any]],
    vehicle_id: UUID | None,
) -> dict[str, Any] | None:
    if vehicle_id is None:
        return None
    for candidate in candidates:
        if candidate["vehicle"]["id"] == vehicle_id:
            return candidate
    return None


def _select_spec(
    specs: list[dict[str, Any]],
    spec_id: UUID | None,
) -> VehicleSpec | None:
    if not specs:
        return None
    if spec_id is None:
        selected = min(
            specs,
            key=lambda item: (
                not bool(item.get("is_default")),
                item.get("variant_key") or "",
                str(item["id"]),
            ),
        )
        return VehicleSpec.model_validate(selected)
    for spec in specs:
        if spec["id"] == spec_id:
            return VehicleSpec.model_validate(spec)
    return None


def _market_reference_price(
    candidate: dict[str, Any],
    vehicle: VehicleSummary,
    spec: VehicleSpec | None,
) -> float | None:
    listings = candidate.get("listings", [])
    exact_spec_listings = (
        [
            listing
            for listing in listings
            if listing.get("spec_id") == spec.id
        ]
        if spec is not None
        else []
    )
    priced_listings = exact_spec_listings
    if not priced_listings and not any(
        listing.get("spec_id") is not None for listing in listings
    ):
        priced_listings = listings
    listing_prices = [
        _as_float(listing.get("price_eur"))
        for listing in priced_listings
        if listing.get("price_eur") is not None
    ]
    if listing_prices:
        return round(mean(listing_prices), 2)
    if spec is not None and spec.list_price_eur is not None:
        return spec.list_price_eur
    return _as_float(vehicle.base_price_eur)


def _assess_price(
    *,
    asking_price: float | None,
    reference_price: float | None,
) -> tuple[str, list[str], list[str]]:
    if asking_price is None or reference_price is None:
        return "unknown", [], []
    if asking_price > reference_price * 1.10:
        return (
            "above_range",
            ["asking_price_above_market_reference"],
            ["asking_price_above_reference"],
        )
    if asking_price < reference_price * 0.75:
        return (
            "below_range",
            ["asking_price_below_market_reference"],
            [],
        )
    return "in_range", [], []


def _estimate_costs(
    *,
    request: ModelAnalysisRequest,
    vehicle: VehicleSummary,
    spec: VehicleSpec | None,
    reference_price: float | None,
    missing_data: list[str],
    include_price: bool,
    include_maintenance: bool,
    include_tco: bool,
    analysis_year: int,
) -> ModelAnalysisCostSummary:
    annual_km = _annual_km(request.usage_profile)
    maintenance = (
        _annual_maintenance(vehicle, spec, request.current_km, analysis_year)
        if include_maintenance
        else None
    )
    monthly_energy = (
        _monthly_energy_cost(vehicle, spec, annual_km) if include_tco else None
    )
    depreciation = (
        _depreciation_3y(
            request.asking_price_eur or reference_price or vehicle.base_price_eur
        )
        if include_tco
        else None
    )
    notes = [f"annual_km_assumption:{annual_km}"]

    if include_price and reference_price is None:
        missing_data.append("market_reference_price_eur")
    if include_tco and monthly_energy is None:
        missing_data.append("energy_consumption")
        notes.append("energy_cost_not_estimated")

    return ModelAnalysisCostSummary(
        market_reference_price_eur=reference_price if include_price else None,
        estimated_annual_maintenance_eur=maintenance,
        estimated_monthly_energy_eur=monthly_energy,
        estimated_depreciation_3y_eur=depreciation,
        notes=notes,
    )


def _annual_km(usage_profile: list[str]) -> int:
    if not usage_profile:
        return 12000
    profile_values = {
        "city": 10000,
        "mixed": 12000,
        "family": 14000,
        "highway": 18000,
        "work": 18000,
    }
    return max(profile_values.get(profile, 12000) for profile in usage_profile)


def _annual_maintenance(
    vehicle: VehicleSummary,
    spec: VehicleSpec | None,
    current_km: int | None,
    analysis_year: int,
) -> float:
    body_style = spec.body_style if spec and spec.body_style else vehicle.body_style
    fuel_type = spec.fuel_type if spec and spec.fuel_type else vehicle.fuel_type
    return estimate_annual_maintenance(
        model_year=vehicle.model_year,
        current_km=current_km,
        body_style=body_style,
        fuel_type=fuel_type,
        analysis_year=analysis_year,
    )


def estimate_annual_maintenance(
    *,
    model_year: int,
    current_km: int | None,
    body_style: str | None,
    fuel_type: str | None,
    analysis_year: int,
) -> float:
    """Deterministic maintenance estimate shared with TCO V1."""
    age = max(1, analysis_year - model_year)
    km_factor = (current_km or 0) / 1000 * 2.5
    base_cost = 420 if body_style == "city_car" else 520
    if fuel_type == "electric":
        base_cost = 340
    return round(base_cost + age * 70 + km_factor, 2)


def _monthly_energy_cost(
    vehicle: VehicleSummary,
    spec: VehicleSpec | None,
    annual_km: int,
) -> float | None:
    fuel_type = spec.fuel_type if spec and spec.fuel_type else vehicle.fuel_type
    if fuel_type == "electric":
        if spec is None or spec.energy_consumption_kwh_100km is None:
            return None
        kwh = annual_km * spec.energy_consumption_kwh_100km / 100
        return round((kwh * ELECTRICITY_PRICE_EUR_PER_KWH) / 12, 2)
    if spec and spec.consumption_l_100km is not None:
        liters = annual_km * spec.consumption_l_100km / 100
        return round((liters * DEFAULT_FUEL_PRICE_EUR_PER_LITER) / 12, 2)
    return None


def _depreciation_3y(price: float | Decimal | None) -> float | None:
    normalized_price = _as_float(price)
    if normalized_price is None:
        return None
    return round(normalized_price * 0.28, 2)


def _is_high_mileage(
    model_year: int,
    current_km: int,
    usage_profile: list[str],
    analysis_year: int,
) -> bool:
    vehicle_age = max(1, analysis_year - model_year)
    expected_km = _annual_km(usage_profile) * vehicle_age
    return current_km > expected_km * 1.35


def _build_checklist(
    vehicle: VehicleSummary,
    spec: VehicleSpec | None,
    red_flags: list[str],
) -> list[str]:
    checklist = [
        "verify_service_history",
        "inspect_brakes_and_tires",
        "confirm_no_warning_lights",
    ]
    fuel_type = spec.fuel_type if spec and spec.fuel_type else vehicle.fuel_type
    if fuel_type == "electric":
        checklist.append("check_battery_health_report")
    if fuel_type in {
        "full_hybrid_petrol",
        "hybrid_petrol",
        "mild_hybrid_petrol",
    }:
        checklist.append("check_hybrid_system_diagnostics")
    if spec and spec.transmission:
        checklist.append("test_transmission_shift_quality")
    if "asking_price_above_reference" in red_flags:
        checklist.append("negotiate_against_reference_price")
    return checklist


def _build_verdict(
    missing_data: list[str],
    required_inputs: set[str],
    price_assessment: str,
    red_flags: list[str],
) -> str:
    critical_missing = {"resolved_vehicle", *required_inputs}
    if critical_missing & set(missing_data):
        return "not_enough_data"
    if price_assessment == "above_range" or "high_mileage_for_age" in red_flags:
        return "risky_at_price"
    return "interesting_with_checks"


def _confidence(
    *,
    resolution_confidence: float,
    missing_data: list[str],
    warnings: list[str],
) -> float:
    confidence = min(resolution_confidence, 0.9)
    confidence -= 0.08 * len(set(missing_data))
    confidence -= 0.04 * len(set(warnings))
    return round(max(0.0, min(confidence, 0.92)), 2)


def _status(
    *,
    confidence: float,
    missing_data: list[str],
    warnings: list[str],
    required_inputs: set[str],
) -> str:
    critical_missing = {"resolved_vehicle", *required_inputs}
    if critical_missing & set(missing_data):
        return "needs_input"
    if "vehicle_resolution_ambiguous" in warnings or confidence < 0.7:
        return "low_confidence"
    return "completed"


def _next_actions(status: str, red_flags: list[str]) -> list[str]:
    if status == "needs_input":
        return ["modify_parameters"]
    actions = ["modify_parameters", "open_checklist", "compare_alternatives"]
    if not red_flags:
        return actions
    return [*actions, "generate_report"]


def _as_float(value: float | Decimal | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)
