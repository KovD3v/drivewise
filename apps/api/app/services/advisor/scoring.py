from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.schemas.advisor import (
    AdvisorFactor,
    AdvisorMetricProvenance,
    AdvisorOffer,
    AdvisorRecommendationGroup,
    AdvisorRecommendationItem,
    AdvisorRecommendationRequest,
    AdvisorScoreComponent,
    AdvisorSelectedSpec,
    AdvisorVehicleSummary,
)
from app.services.advisor.energy_prices import (
    ARERA_SOURCE_NAME,
    ARERA_SOURCE_URL,
    ELECTRICITY_PRICE_EUR_PER_KWH,
    ENERGY_ASSUMPTION_VERSION,
    ENERGY_ASSUMPTIONS,
    ENERGY_PRICES_OBSERVED_AT,
    LIQUID_ENERGY_PRICES_EUR_PER_LITER,
    MIMIT_SOURCE_NAME,
    MIMIT_SOURCE_URL,
)


SCORING_VERSION = "advisor-v2.0"
FRESHNESS_DAYS = 30
MAX_ITEMS_PER_GROUP = 5

BASE_WEIGHTS: dict[AdvisorScoreComponent, float] = {
    "price_fit": 30.0,
    "use_case_fit": 25.0,
    "running_cost": 20.0,
    "space": 15.0,
    "efficiency_range": 10.0,
}
PRIORITY_COMPONENT: dict[str, AdvisorScoreComponent] = {
    "price": "price_fit",
    "running_cost": "running_cost",
    "space": "space",
    "efficiency_range": "efficiency_range",
}

BODY_USE_MATRIX: dict[str, dict[str, float]] = {
    "city": {
        "city_car": 100,
        "small_hatchback": 95,
        "hatchback": 80,
        "crossover": 60,
        "sedan": 55,
        "wagon": 45,
        "suv": 40,
        "mpv": 35,
        "van": 20,
    },
    "family": {
        "mpv": 100,
        "wagon": 100,
        "suv": 100,
        "crossover": 90,
        "hatchback": 75,
        "sedan": 75,
        "van": 70,
        "small_hatchback": 45,
        "city_car": 25,
    },
    "highway": {
        "sedan": 100,
        "wagon": 100,
        "hatchback": 85,
        "crossover": 80,
        "suv": 80,
        "mpv": 75,
        "small_hatchback": 60,
        "van": 50,
        "city_car": 35,
    },
    "work": {
        "van": 100,
        "wagon": 90,
        "suv": 80,
        "mpv": 80,
        "crossover": 75,
        "hatchback": 60,
        "sedan": 60,
        "small_hatchback": 45,
        "city_car": 30,
    },
}

EXCLUSION_REASON_ORDER = (
    "non_it_market",
    "source_not_permitted",
    "inactive_offer",
    "stale_offer",
    "expired_offer",
    "unreviewed_source",
    "unresolved_spec",
    "missing_model_family_key",
    "missing_spec_provenance",
    "missing_price",
    "invalid_condition",
    "condition_mismatch",
    "below_budget_min",
    "above_budget_tolerance",
    "missing_mileage",
    "above_max_mileage",
    "missing_body_style",
    "missing_fuel_type",
    "unsupported_phev",
    "unsupported_fuel_type",
    "unsupported_body_style",
    "missing_seats",
    "missing_cargo",
    "missing_liquid_consumption",
    "missing_ev_consumption",
    "missing_ev_range",
    "insufficient_highway_ev_range",
)


@dataclass(frozen=True)
class AdvisorScoringResult:
    groups: list[AdvisorRecommendationGroup]
    excluded_counts_by_reason: dict[str, int]
    weights: dict[AdvisorScoreComponent, float]

    @property
    def items(self) -> list[AdvisorRecommendationItem]:
        return [item for group in self.groups for item in group.items]


def build_assumptions(request: AdvisorRecommendationRequest) -> list[str]:
    assert request.annual_km is not None
    annual_km_source = (
        f"default for primary_use={request.primary_use}"
        if request.annual_km_was_defaulted
        else "provided by the request"
    )
    return [
        (
            f"Annual distance: {request.annual_km} km ({annual_km_source}); "
            "used only for the annual energy-cost estimate."
        ),
        (
            "The running_cost component covers energy only; maintenance, tax, "
            "insurance, depreciation, and financing are excluded."
        ),
        *ENERGY_ASSUMPTIONS,
    ]


def score_recommendations(
    request: AdvisorRecommendationRequest,
    candidates: list[dict[str, Any]],
    *,
    as_of: datetime | None = None,
    initial_excluded_counts: dict[str, int] | None = None,
) -> AdvisorScoringResult:
    evaluation_time = _as_aware_datetime(as_of) or datetime.now(timezone.utc)
    excluded = Counter(initial_excluded_counts or {})
    weights = _normalized_weights(request)
    scored_by_group: dict[str, list[AdvisorRecommendationItem]] = {
        "new": [],
        "used": [],
    }

    for candidate in _expand_exact_pairs(candidates):
        reason = _exclusion_reason(request, candidate, evaluation_time)
        if reason is not None:
            excluded[reason] += 1
            continue

        item = _score_candidate(request, candidate, weights)
        group_name = "new" if item.offer.condition == "new" else "used"
        scored_by_group[group_name].append(item)

    requested_groups = (
        ["new", "used"] if request.condition == "any" else [request.condition]
    )
    groups: list[AdvisorRecommendationGroup] = []
    for group_name in requested_groups:
        ranked = sorted(scored_by_group[group_name], key=_stable_rank_key)
        selected: list[AdvisorRecommendationItem] = []
        seen_families: set[str] = set()
        for item in ranked:
            family_key = item.vehicle.model_family_key
            if family_key is None or family_key in seen_families:
                continue
            seen_families.add(family_key)
            selected.append(item)
            if len(selected) == MAX_ITEMS_PER_GROUP:
                break
        groups.append(
            AdvisorRecommendationGroup(condition=group_name, items=selected)
        )

    ordered_exclusions = {
        reason: excluded[reason]
        for reason in EXCLUSION_REASON_ORDER
        if excluded[reason] > 0
    }
    for reason in sorted(set(excluded) - set(EXCLUSION_REASON_ORDER)):
        if excluded[reason] > 0:
            ordered_exclusions[reason] = excluded[reason]

    return AdvisorScoringResult(
        groups=groups,
        excluded_counts_by_reason=ordered_exclusions,
        weights=weights,
    )


def build_recommendations(
    request: AdvisorRecommendationRequest,
    candidates: list[dict[str, Any]],
    *,
    as_of: datetime | None = None,
) -> list[AdvisorRecommendationItem]:
    """Compatibility wrapper returning the flattened Advisor v2 ranking."""
    return score_recommendations(request, candidates, as_of=as_of).items


def _expand_exact_pairs(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for candidate in candidates:
        if "spec" in candidate or "offer" in candidate:
            pairs.append(candidate)
            continue

        specs = candidate.get("specs") or []
        listings = candidate.get("listings") or []
        specs_by_id = {str(spec.get("id")): spec for spec in specs if spec.get("id")}
        for offer in listings:
            spec_id = offer.get("spec_id")
            spec = specs_by_id.get(str(spec_id)) if spec_id is not None else None
            pairs.append(
                {
                    "vehicle": candidate.get("vehicle"),
                    "spec": spec,
                    "offer": offer,
                    "provenance": candidate.get("provenance", []),
                    "reviewed": candidate.get("reviewed", False),
                    "repository_eligible": candidate.get(
                        "repository_eligible",
                        False,
                    ),
                }
            )
    return pairs


def _exclusion_reason(
    request: AdvisorRecommendationRequest,
    candidate: dict[str, Any],
    as_of: datetime,
) -> str | None:
    vehicle = candidate.get("vehicle") or {}
    spec = candidate.get("spec") or {}
    offer = candidate.get("offer") or {}

    if str(vehicle.get("market", "")).upper() != "IT":
        return "non_it_market"
    if offer.get("is_active") is not True:
        return "inactive_offer"

    last_seen = _as_aware_datetime(offer.get("last_seen_at"))
    if last_seen is None or last_seen < as_of - timedelta(days=FRESHNESS_DAYS):
        return "stale_offer"
    valid_until = _as_aware_datetime(offer.get("valid_until"))
    if valid_until is not None and valid_until < as_of:
        return "expired_offer"

    source = candidate.get("source") or {}
    if source.get("ranking_permission") != "permitted":
        return "source_not_permitted"
    if not _is_reviewed(candidate, offer):
        return "unreviewed_source"

    if (
        not spec
        or offer.get("spec_id") is None
        or str(offer.get("spec_id")) != str(spec.get("id"))
        or str(offer.get("vehicle_id")) != str(vehicle.get("id"))
        or not _nonblank(spec.get("variant_key"))
    ):
        return "unresolved_spec"
    if not _nonblank(vehicle.get("model_family_key")):
        return "missing_model_family_key"

    price = _number(offer.get("price_eur"))
    if price is None:
        return "missing_price"

    condition = offer.get("condition")
    if condition not in {"new", "used", "certified"}:
        return "invalid_condition"
    grouped_condition = "new" if condition == "new" else "used"
    if request.condition != "any" and grouped_condition != request.condition:
        return "condition_mismatch"

    if request.budget_min_eur is not None and price < request.budget_min_eur:
        return "below_budget_min"
    if price > request.budget_max_eur * 1.10:
        return "above_budget_tolerance"

    mileage = _integer(offer.get("mileage"))
    if grouped_condition == "used" and mileage is None:
        return "missing_mileage"
    if (
        grouped_condition == "used"
        and request.max_mileage is not None
        and mileage is not None
        and mileage > request.max_mileage
    ):
        return "above_max_mileage"

    body_style = spec.get("body_style")
    if not _nonblank(body_style):
        return "missing_body_style"
    fuel_type = spec.get("fuel_type")
    if not _nonblank(fuel_type):
        return "missing_fuel_type"
    if _is_phev(str(fuel_type)):
        return "unsupported_phev"
    if fuel_type not in LIQUID_ENERGY_PRICES_EUR_PER_LITER and fuel_type != "electric":
        return "unsupported_fuel_type"
    if body_style not in BODY_USE_MATRIX["city"]:
        return "unsupported_body_style"
    if _positive_number(spec.get("seats")) is None:
        return "missing_seats"
    if _nonnegative_number(spec.get("cargo_volume_liters")) is None:
        return "missing_cargo"

    if fuel_type == "electric":
        if _positive_number(spec.get("energy_consumption_kwh_100km")) is None:
            return "missing_ev_consumption"
        ev_range = _positive_number(spec.get("wltp_range_km"))
        if ev_range is None:
            return "missing_ev_range"
        if request.primary_use == "highway" and ev_range < 250:
            return "insufficient_highway_ev_range"
    elif _positive_number(spec.get("consumption_l_100km")) is None:
        return "missing_liquid_consumption"

    if not _has_spec_provenance(candidate, spec):
        return "missing_spec_provenance"

    return None


def _is_reviewed(candidate: dict[str, Any], offer: dict[str, Any]) -> bool:
    source = candidate.get("source") or {}
    if source.get("ranking_permission") != "permitted":
        return False
    if candidate.get("reviewed") is True:
        return True
    import_status = candidate.get("import_status")
    return (
        _nonblank(offer.get("source_url"))
        and _nonblank(source.get("name"))
        and _nonblank(source.get("license"))
        and import_status == "completed"
    )


def _has_spec_provenance(
    candidate: dict[str, Any],
    spec: dict[str, Any],
) -> bool:
    required_metrics = {
        "body_style",
        "fuel_type",
        "seats",
        "cargo_volume_liters",
    }
    if spec.get("fuel_type") == "electric":
        required_metrics.update(
            {"energy_consumption_kwh_100km", "wltp_range_km"}
        )
    else:
        required_metrics.add("consumption_l_100km")

    covered_metrics = {
        entry["metric"]
        for entry in candidate.get("provenance", [])
        if isinstance(entry, dict)
        and entry.get("metric") in required_metrics
        and _nonblank(entry.get("source_name"))
        and _nonblank(entry.get("source_url"))
        and entry.get("observed_at") is not None
    }
    return required_metrics <= covered_metrics


def _score_candidate(
    request: AdvisorRecommendationRequest,
    candidate: dict[str, Any],
    weights: dict[AdvisorScoreComponent, float],
) -> AdvisorRecommendationItem:
    vehicle_data = candidate["vehicle"]
    spec_data = candidate["spec"]
    offer_data = candidate["offer"]

    price = float(offer_data["price_eur"])
    body_style = str(spec_data["body_style"])
    fuel_type = str(spec_data["fuel_type"])
    seats = float(spec_data["seats"])
    cargo = float(spec_data["cargo_volume_liters"])
    consumption = _number(spec_data.get("consumption_l_100km"))
    electric_consumption = _number(
        spec_data.get("energy_consumption_kwh_100km")
    )
    ev_range = _number(spec_data.get("wltp_range_km"))

    energy_rate, energy_rate_metric = _energy_rate(fuel_type)
    energy_consumption = (
        electric_consumption if fuel_type == "electric" else consumption
    )
    assert energy_consumption is not None
    cost_100km = energy_consumption * energy_rate
    assert request.annual_km is not None
    annual_energy_cost = cost_100km * request.annual_km / 100

    raw_scores: dict[AdvisorScoreComponent, float] = {
        "price_fit": _price_score(price, request.budget_max_eur),
        "use_case_fit": _use_case_score(
            request,
            body_style=body_style,
            fuel_type=fuel_type,
        ),
        "running_cost": _descending_linear_score(cost_100km, 5.0, 15.0),
        "space": _space_score(
            request.primary_use,
            seats=seats,
            cargo=cargo,
        ),
        "efficiency_range": _efficiency_score(
            fuel_type=fuel_type,
            consumption=consumption,
            electric_consumption=electric_consumption,
            ev_range=ev_range,
        ),
    }
    component_scores = {
        component: round(score, 2) for component, score in raw_scores.items()
    }
    final_score = round(
        sum(raw_scores[name] * weights[name] / 100 for name in BASE_WEIGHTS),
        2,
    )

    budget_overrun = max(0.0, price - request.budget_max_eur)
    budget_overrun_percent = budget_overrun / request.budget_max_eur * 100
    evidence: dict[str, Any] = {
        "price_eur": round(price, 2),
        "budget_max_eur": request.budget_max_eur,
        "budget_overrun_eur": round(budget_overrun, 2),
        "budget_overrun_percent": round(budget_overrun_percent, 2),
        "annual_km": request.annual_km,
        "mileage": offer_data.get("mileage"),
        "body_style": body_style,
        "fuel_type": fuel_type,
        "seats": int(seats),
        "cargo_volume_liters": round(cargo, 2),
        "energy_cost_eur_100km": round(cost_100km, 2),
        "annual_energy_cost_eur": round(annual_energy_cost, 2),
        "energy_assumption_version": ENERGY_ASSUMPTION_VERSION,
        "energy_rate": round(energy_rate, 5),
        "energy_rate_metric": energy_rate_metric,
        "normalized_weights": {
            component: round(weight, 6) for component, weight in weights.items()
        },
    }
    if request.budget_min_eur is not None:
        evidence["budget_min_eur"] = request.budget_min_eur
    if request.max_mileage is not None:
        evidence["max_mileage"] = request.max_mileage
    if consumption is not None:
        evidence["consumption_l_100km"] = round(consumption, 2)
    if electric_consumption is not None:
        evidence["energy_consumption_kwh_100km"] = round(
            electric_consumption,
            2,
        )
    if ev_range is not None:
        evidence["wltp_range_km"] = int(ev_range)

    positive_factors, tradeoffs = _build_factors(
        request=request,
        component_scores=raw_scores,
        weights=weights,
        evidence=evidence,
    )

    return AdvisorRecommendationItem(
        vehicle=AdvisorVehicleSummary.model_validate(vehicle_data),
        selected_spec=AdvisorSelectedSpec.model_validate(spec_data),
        offer=AdvisorOffer.model_validate(offer_data),
        score=final_score,
        component_scores=component_scores,
        positive_factors=positive_factors,
        tradeoffs=tradeoffs,
        evidence=evidence,
        provenance=_build_provenance(candidate, fuel_type),
    )


def _normalized_weights(
    request: AdvisorRecommendationRequest,
) -> dict[AdvisorScoreComponent, float]:
    selected_components = {
        PRIORITY_COMPONENT[priority] for priority in request.priorities
    }
    adjusted = {
        component: weight * (1.5 if component in selected_components else 1.0)
        for component, weight in BASE_WEIGHTS.items()
    }
    total = sum(adjusted.values())
    return {component: weight * 100 / total for component, weight in adjusted.items()}


def _price_score(price: float, ceiling: float) -> float:
    ratio = price / ceiling
    if ratio <= 0.75:
        return 100.0
    if ratio <= 1.0:
        return 100 - ((ratio - 0.75) / 0.25) * 30
    return max(0.0, 70 - ((ratio - 1.0) / 0.10) * 70)


def _use_case_score(
    request: AdvisorRecommendationRequest,
    *,
    body_style: str,
    fuel_type: str,
) -> float:
    use_key = "city" if request.primary_use == "new_driver" else request.primary_use
    body_fit = BODY_USE_MATRIX[use_key].get(body_style, 0.0)
    fuel_preference = (
        100.0
        if request.preferred_fuel_type is None
        or request.preferred_fuel_type == fuel_type
        else 0.0
    )
    body_preference = (
        100.0
        if request.preferred_body_style is None
        or request.preferred_body_style == body_style
        else 0.0
    )
    return 0.60 * body_fit + 0.20 * fuel_preference + 0.20 * body_preference


def _space_score(primary_use: str, *, seats: float, cargo: float) -> float:
    required_seats = 5 if primary_use in {"family", "work"} else 4
    seat_score = min(seats / required_seats * 100, 100)
    cargo_bands = {
        "city": (150.0, 350.0),
        "new_driver": (150.0, 350.0),
        "highway": (200.0, 450.0),
        "family": (250.0, 500.0),
        "work": (250.0, 500.0),
    }
    low, high = cargo_bands[primary_use]
    cargo_score = _ascending_linear_score(cargo, low, high)
    return 0.40 * seat_score + 0.60 * cargo_score


def _efficiency_score(
    *,
    fuel_type: str,
    consumption: float | None,
    electric_consumption: float | None,
    ev_range: float | None,
) -> float:
    if fuel_type != "electric":
        assert consumption is not None
        return _descending_linear_score(consumption, 4.0, 8.0)
    assert electric_consumption is not None and ev_range is not None
    efficiency = _descending_linear_score(electric_consumption, 14.0, 24.0)
    range_score = _ascending_linear_score(ev_range, 150.0, 500.0)
    return (efficiency + range_score) / 2


def _descending_linear_score(value: float, best: float, worst: float) -> float:
    if value <= best:
        return 100.0
    if value >= worst:
        return 0.0
    return (worst - value) / (worst - best) * 100


def _ascending_linear_score(value: float, low: float, high: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return 100.0
    return (value - low) / (high - low) * 100


def _energy_rate(fuel_type: str) -> tuple[float, str]:
    if fuel_type == "electric":
        return ELECTRICITY_PRICE_EUR_PER_KWH, "electricity_price_eur_kwh"
    return LIQUID_ENERGY_PRICES_EUR_PER_LITER[fuel_type], "fuel_price_eur_liter"


def _build_factors(
    *,
    request: AdvisorRecommendationRequest,
    component_scores: dict[AdvisorScoreComponent, float],
    weights: dict[AdvisorScoreComponent, float],
    evidence: dict[str, Any],
) -> tuple[list[AdvisorFactor], list[AdvisorFactor]]:
    positive_messages = {
        "price_fit": "Il prezzo usa bene il budget disponibile.",
        "use_case_fit": "Carrozzeria e preferenze sono adatte all'uso principale.",
        "running_cost": "Il costo energia stimato e contenuto.",
        "space": "Posti e bagagliaio offrono una buona versatilita.",
        "efficiency_range": "Efficienza e autonomia sono competitive.",
    }
    tradeoff_messages = {
        "price_fit": "Il prezzo lascia poco margine nel budget.",
        "use_case_fit": "Carrozzeria o preferenze si adattano poco all'uso.",
        "running_cost": "Il costo energia stimato e elevato.",
        "space": "Posti o bagagliaio sono sotto la fascia piu versatile.",
        "efficiency_range": "Efficienza o autonomia sono sotto la fascia migliore.",
    }
    factor_metrics = {
        "price_fit": ("price_eur", evidence["price_eur"], request.budget_max_eur),
        "use_case_fit": (
            "body_style",
            evidence["body_style"],
            request.primary_use,
        ),
        "running_cost": (
            "energy_cost_eur_100km",
            evidence["energy_cost_eur_100km"],
            15.0,
        ),
        "space": (
            "cargo_volume_liters",
            evidence["cargo_volume_liters"],
            _cargo_high_band(request.primary_use),
        ),
        "efficiency_range": _efficiency_factor_metric(evidence),
    }

    positives: list[AdvisorFactor] = []
    tradeoffs: list[AdvisorFactor] = []
    for component in BASE_WEIGHTS:
        component_score = component_scores[component]
        contribution = round(weights[component] * component_score / 100, 2)
        metric, value, threshold = factor_metrics[component]
        if component_score >= 80:
            positives.append(
                AdvisorFactor(
                    component=component,
                    message=positive_messages[component],
                    metric=metric,
                    value=value,
                    threshold=threshold,
                    contribution=contribution,
                )
            )
        if component_score < 70:
            message = tradeoff_messages[component]
            if component == "price_fit" and evidence["budget_overrun_eur"] > 0:
                message = (
                    "Il prezzo supera il budget massimo di "
                    f"EUR {evidence['budget_overrun_eur']:.2f} "
                    f"({evidence['budget_overrun_percent']:.2f}%)."
                )
                metric = "budget_overrun_eur"
                value = evidence["budget_overrun_eur"]
                threshold = request.budget_max_eur
            tradeoffs.append(
                AdvisorFactor(
                    component=component,
                    message=message,
                    metric=metric,
                    value=value,
                    threshold=threshold,
                    contribution=contribution,
                )
            )

    if evidence["budget_overrun_eur"] > 0 and not any(
        factor.component == "price_fit" for factor in tradeoffs
    ):
        price_score = component_scores["price_fit"]
        tradeoffs.insert(
            0,
            AdvisorFactor(
                component="price_fit",
                message=(
                    "Il prezzo supera il budget massimo di "
                    f"EUR {evidence['budget_overrun_eur']:.2f} "
                    f"({evidence['budget_overrun_percent']:.2f}%)."
                ),
                metric="budget_overrun_eur",
                value=evidence["budget_overrun_eur"],
                threshold=request.budget_max_eur,
                contribution=round(weights["price_fit"] * price_score / 100, 2),
            ),
        )
    return positives, tradeoffs


def _efficiency_factor_metric(
    evidence: dict[str, Any],
) -> tuple[str, float, float]:
    if "energy_consumption_kwh_100km" in evidence:
        return (
            "energy_consumption_kwh_100km",
            evidence["energy_consumption_kwh_100km"],
            14.0,
        )
    return (
        "consumption_l_100km",
        evidence["consumption_l_100km"],
        4.0,
    )


def _cargo_high_band(primary_use: str) -> int:
    return 350 if primary_use in {"city", "new_driver"} else 450 if primary_use == "highway" else 500


def _build_provenance(
    candidate: dict[str, Any],
    fuel_type: str,
) -> list[AdvisorMetricProvenance]:
    entries: list[AdvisorMetricProvenance] = []
    seen: set[tuple[str, str, str | None, str | None]] = set()
    for raw_entry in candidate.get("provenance", []):
        entry = AdvisorMetricProvenance.model_validate(raw_entry)
        observed_at = (
            entry.observed_at.isoformat() if entry.observed_at is not None else None
        )
        key = (entry.metric, entry.source_name, entry.source_url, observed_at)
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)

    energy_entry = AdvisorMetricProvenance(
        metric=(
            "electricity_price_eur_kwh"
            if fuel_type == "electric"
            else "fuel_price_eur_liter"
        ),
        source_name=(ARERA_SOURCE_NAME if fuel_type == "electric" else MIMIT_SOURCE_NAME),
        source_url=(ARERA_SOURCE_URL if fuel_type == "electric" else MIMIT_SOURCE_URL),
        observed_at=ENERGY_PRICES_OBSERVED_AT,
    )
    observed_at = energy_entry.observed_at.isoformat()
    energy_key = (
        energy_entry.metric,
        energy_entry.source_name,
        energy_entry.source_url,
        observed_at,
    )
    if energy_key not in seen:
        entries.append(energy_entry)

    return sorted(
        entries,
        key=lambda entry: (
            entry.metric,
            entry.source_name,
            entry.source_url or "",
        ),
    )


def _stable_rank_key(item: AdvisorRecommendationItem) -> tuple[Any, ...]:
    return (
        -item.score,
        item.offer.price_eur,
        item.vehicle.make.casefold(),
        item.vehicle.model.casefold(),
        str(item.offer.id),
    )


def _is_phev(fuel_type: str) -> bool:
    normalized = fuel_type.casefold().replace("-", "_")
    return "plug_in" in normalized or "plugin" in normalized or normalized == "phev"


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    return None


def _positive_number(value: Any) -> float | None:
    normalized = _number(value)
    return normalized if normalized is not None and normalized > 0 else None


def _nonnegative_number(value: Any) -> float | None:
    normalized = _number(value)
    return normalized if normalized is not None and normalized >= 0 else None


def _integer(value: Any) -> int | None:
    normalized = _number(value)
    if normalized is None or normalized < 0 or not normalized.is_integer():
        return None
    return int(normalized)


def _as_aware_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            value = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
