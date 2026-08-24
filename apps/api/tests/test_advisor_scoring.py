from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.scoring import (
    ARERA_SOURCE_NAME,
    ELECTRICITY_PRICE_EUR_PER_KWH,
    ENERGY_ASSUMPTION_VERSION,
    LIQUID_ENERGY_PRICES_EUR_PER_LITER,
    build_assumptions,
    score_recommendations,
)


AS_OF = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)


def candidate(
    index: int,
    *,
    make: str = "Acme",
    model: str | None = None,
    model_family_key: str | None = None,
    body_style: str = "hatchback",
    fuel_type: str = "petrol",
    price_eur: float | None = 18_000,
    condition: str = "used",
    mileage: int | None = 10_000,
    seats: int | None = 5,
    cargo: float | None = 350,
    consumption: float | None = 5.0,
    electric_consumption: float | None = None,
    ev_range: int | None = None,
    reviewed: bool = True,
) -> dict[str, Any]:
    model_name = model or f"Model {index:02d}"
    family = model_family_key or f"it-acme-model-{index:02d}"
    vehicle_id = UUID(f"00000000-0000-4000-8000-{index:012d}")
    spec_id = UUID(f"20000000-0000-4000-8000-{index:012d}")
    offer_id = UUID(f"30000000-0000-4000-8000-{index:012d}")
    return {
        "vehicle": {
            "id": vehicle_id,
            "canonical_key": f"it-acme-model-{index:02d}-2026",
            "model_family_key": family,
            "make": make,
            "model": model_name,
            "model_year": 2026,
            "body_style": body_style,
            "fuel_type": fuel_type,
            "market": "IT",
            "base_price_eur": price_eur,
        },
        "spec": {
            "id": spec_id,
            "variant_key": f"it-acme-model-{index:02d}-test",
            "is_default": True,
            "trim": "Test",
            "body_style": body_style,
            "fuel_type": fuel_type,
            "list_price_eur": price_eur,
            "drivetrain": "fwd",
            "transmission": "automatic",
            "engine": "test",
            "horsepower": 100,
            "battery_kwh": 50 if fuel_type == "electric" else None,
            "energy_consumption_kwh_100km": electric_consumption,
            "consumption_l_100km": consumption,
            "wltp_range_km": ev_range,
            "co2_g_km": 0 if fuel_type == "electric" else 110,
            "euro_emission_standard": None
            if fuel_type == "electric"
            else "Euro 6e",
            "seats": seats,
            "cargo_volume_liters": cargo,
        },
        "offer": {
            "id": offer_id,
            "vehicle_id": vehicle_id,
            "spec_id": spec_id,
            "source_id": UUID("10000000-0000-4000-8000-000000000001"),
            "listing_ref": f"offer-{index:02d}",
            "title": f"{make} {model_name}",
            "price_eur": price_eur,
            "mileage": mileage,
            "condition": condition,
            "location_region": "Lazio",
            "source_url": f"https://example.test/offers/{index}",
            "listed_at": "2026-07-10",
            "last_seen_at": "2026-07-16T09:00:00Z",
            "valid_until": "2026-08-16T00:00:00Z",
            "is_active": True,
        },
        "reviewed": reviewed,
        "source": {
            "name": "Reviewed catalog",
            "license": "Synthetic test data",
            "ranking_permission": "permitted",
        },
        "provenance": [
            {
                "metric": metric,
                "source_name": "Reviewed catalog",
                "source_url": f"https://example.test/specs/{index}",
                "observed_at": "2026-07-15T00:00:00Z",
            }
            for metric in [
                "body_style",
                "fuel_type",
                "seats",
                "cargo_volume_liters",
                *(
                    ["energy_consumption_kwh_100km", "wltp_range_km"]
                    if fuel_type == "electric"
                    else ["consumption_l_100km"]
                ),
            ]
        ],
    }


def items_by_model(result) -> dict[str, Any]:
    return {item.vehicle.model: item for item in result.items}


def test_gold_01_price_curve_100_105_110_111_and_exact_overrun_factor():
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
    )
    result = score_recommendations(
        request,
        [
            candidate(1, price_eur=20_000),
            candidate(2, price_eur=21_000),
            candidate(3, price_eur=22_000),
            candidate(4, price_eur=22_200),
        ],
        as_of=AS_OF,
    )

    by_model = items_by_model(result)
    assert by_model["Model 01"].component_scores["price_fit"] == 70
    assert by_model["Model 02"].component_scores["price_fit"] == 35
    assert by_model["Model 03"].component_scores["price_fit"] == 0
    assert result.excluded_counts_by_reason == {"above_budget_tolerance": 1}
    price_tradeoff = next(
        factor
        for factor in by_model["Model 03"].tradeoffs
        if factor.component == "price_fit"
    )
    assert price_tradeoff.value == 2_000
    assert "10.00%" in price_tradeoff.message


def test_gold_02_budget_min_and_max_tolerance_are_hard_exclusions():
    request = AdvisorRecommendationRequest(
        budget_min_eur=15_000,
        budget_max_eur=20_000,
        primary_use="city",
    )
    result = score_recommendations(
        request,
        [
            candidate(1, price_eur=14_999),
            candidate(2, price_eur=16_000),
            candidate(3, price_eur=22_001),
        ],
        as_of=AS_OF,
    )

    assert [item.vehicle.model for item in result.items] == ["Model 02"]
    assert result.excluded_counts_by_reason == {
        "below_budget_min": 1,
        "above_budget_tolerance": 1,
    }


def test_gold_03_any_groups_new_and_certified_as_used_without_mismatch_counts():
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
        condition="any",
    )
    candidates = [
        candidate(1, condition="new", mileage=None),
        candidate(2, condition="used"),
        candidate(3, condition="certified"),
    ]
    result = score_recommendations(request, candidates, as_of=AS_OF)

    assert [group.condition for group in result.groups] == ["new", "used"]
    assert [item.offer.condition for item in result.groups[0].items] == ["new"]
    assert {item.offer.condition for item in result.groups[1].items} == {
        "used",
        "certified",
    }
    assert "condition_mismatch" not in result.excluded_counts_by_reason

    new_only = score_recommendations(
        request.model_copy(update={"condition": "new"}),
        candidates,
        as_of=AS_OF,
    )
    assert [group.condition for group in new_only.groups] == ["new"]
    assert new_only.excluded_counts_by_reason == {"condition_mismatch": 2}


def test_gold_04_max_mileage_is_hard_only_for_used_and_used_requires_mileage():
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
        condition="any",
        max_mileage=20_000,
    )
    result = score_recommendations(
        request,
        [
            candidate(1, condition="new", mileage=None),
            candidate(2, condition="used", mileage=None),
            candidate(3, condition="used", mileage=20_001),
            candidate(4, condition="certified", mileage=20_000),
        ],
        as_of=AS_OF,
    )

    assert {item.vehicle.model for item in result.items} == {
        "Model 01",
        "Model 04",
    }
    assert result.excluded_counts_by_reason == {
        "missing_mileage": 1,
        "above_max_mileage": 1,
    }


@pytest.mark.parametrize(
    ("primary_use", "expected"),
    [
        ("city", 10_000),
        ("new_driver", 10_000),
        ("family", 14_000),
        ("highway", 18_000),
        ("work", 18_000),
    ],
)
def test_gold_05_annual_km_defaults_by_primary_use(primary_use, expected):
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use=primary_use,
    )
    assert request.annual_km == expected
    assert request.annual_km_was_defaulted is True


def test_assumptions_disclose_annual_km_source_and_energy_only_scope():
    defaulted = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="family",
    )
    provided = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="family",
        annual_km=12_345,
    )

    assert "14000 km (default for primary_use=family)" in build_assumptions(
        defaulted
    )[0]
    assert "12345 km (provided by the request)" in build_assumptions(provided)[0]
    assert "energy only" in build_assumptions(provided)[1]


def test_gold_06_selected_priorities_scale_and_renormalize_exactly():
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
        priorities=["price", "running_cost"],
    )
    result = score_recommendations(
        request,
        [
            candidate(
                1,
                price_eur=15_000,
                body_style="city_car",
                seats=4,
                cargo=350,
                consumption=5,
            )
        ],
        as_of=AS_OF,
    )
    item = result.items[0]

    assert result.weights == {
        "price_fit": 36,
        "use_case_fit": 20,
        "running_cost": 24,
        "space": 12,
        "efficiency_range": 8,
    }
    assert item.component_scores == {
        "price_fit": 100,
        "use_case_fit": 100,
        "running_cost": 54.17,
        "space": 100,
        "efficiency_range": 75,
    }
    assert item.score == 87.0


def test_gold_07_body_matrix_and_soft_preferences_feed_use_case_component():
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
        preferred_fuel_type="petrol",
        preferred_body_style="city_car",
    )
    result = score_recommendations(
        request,
        [
            candidate(
                1,
                body_style="small_hatchback",
                fuel_type="full_hybrid_petrol",
            )
        ],
        as_of=AS_OF,
    )

    assert result.items[0].component_scores["use_case_fit"] == 57
    assert result.items[0].selected_spec.fuel_type == "full_hybrid_petrol"


def test_gold_08_family_space_is_40_percent_seats_and_60_percent_cargo():
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="family",
    )
    result = score_recommendations(
        request,
        [candidate(1, seats=4, cargo=375)],
        as_of=AS_OF,
    )

    assert result.items[0].component_scores["space"] == 62


def test_gold_09_full_hybrid_uses_petrol_rate_for_efficiency_and_running_cost():
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="family",
    )
    result = score_recommendations(
        request,
        [candidate(1, fuel_type="full_hybrid_petrol", consumption=6)],
        as_of=AS_OF,
    )
    item = result.items[0]

    assert LIQUID_ENERGY_PRICES_EUR_PER_LITER["full_hybrid_petrol"] == 1.91662
    assert item.component_scores["efficiency_range"] == 50
    assert item.component_scores["running_cost"] == 35.0
    assert item.evidence["energy_cost_eur_100km"] == 11.5
    assert item.evidence["annual_energy_cost_eur"] == 1_609.96


def test_gold_10_ev_combines_efficiency_and_range_and_uses_arera_rate():
    request = AdvisorRecommendationRequest(
        budget_max_eur=30_000,
        primary_use="city",
    )
    result = score_recommendations(
        request,
        [
            candidate(
                1,
                fuel_type="electric",
                consumption=None,
                electric_consumption=19,
                ev_range=325,
                price_eur=25_000,
            )
        ],
        as_of=AS_OF,
    )
    item = result.items[0]

    assert ELECTRICITY_PRICE_EUR_PER_KWH == 0.29593
    assert item.component_scores["efficiency_range"] == 50
    assert item.component_scores["running_cost"] == 93.77
    assert item.evidence["annual_energy_cost_eur"] == 562.27
    assert item.evidence["energy_assumption_version"] == ENERGY_ASSUMPTION_VERSION
    assert any(source.source_name == ARERA_SOURCE_NAME for source in item.provenance)


def test_gold_11_strict_eligibility_reports_one_exact_reason_per_offer():
    base = candidate(100)
    cases: list[tuple[str, dict[str, Any]]] = []

    def changed(reason: str, mutation) -> None:
        value = deepcopy(base)
        mutation(value)
        value["vehicle"]["id"] = UUID(
            f"00000000-0000-4000-8000-{len(cases) + 200:012d}"
        )
        value["offer"]["vehicle_id"] = value["vehicle"]["id"]
        if reason != "missing_model_family_key":
            value["vehicle"]["model_family_key"] = (
                f"it-eligibility-{len(cases) + 200}"
            )
        cases.append((reason, value))

    changed("non_it_market", lambda value: value["vehicle"].update(market="EU"))
    changed("inactive_offer", lambda value: value["offer"].update(is_active=False))
    changed(
        "stale_offer",
        lambda value: value["offer"].update(last_seen_at="2026-06-15T00:00:00Z"),
    )
    changed(
        "expired_offer",
        lambda value: value["offer"].update(valid_until="2026-07-16T11:59:00Z"),
    )
    changed(
        "source_not_permitted",
        lambda value: value["source"].update(
            ranking_permission="manual_validation_only"
        ),
    )
    changed("unreviewed_source", lambda value: value.update(reviewed=False))
    changed(
        "unresolved_spec",
        lambda value: value["offer"].update(
            spec_id=UUID("20000000-0000-4000-8000-999999999999")
        ),
    )
    changed(
        "missing_model_family_key",
        lambda value: value["vehicle"].update(model_family_key=""),
    )

    def missing_provenance(value):
        value.update(
            reviewed=False,
            source={
                "name": "Reviewed",
                "license": "CC-BY",
                "ranking_permission": "permitted",
            },
            import_status="completed",
            provenance=[
                {
                    "metric": "trim",
                    "source_name": "Reviewed catalog",
                    "source_url": "https://example.test/specs/trim-only",
                    "observed_at": "2026-07-15T00:00:00Z",
                }
            ],
        )

    changed("missing_spec_provenance", missing_provenance)
    changed("missing_price", lambda value: value["offer"].update(price_eur=None))
    changed(
        "invalid_condition",
        lambda value: value["offer"].update(condition="lease"),
    )
    changed(
        "missing_body_style",
        lambda value: value["spec"].update(body_style=""),
    )
    changed(
        "missing_fuel_type",
        lambda value: value["spec"].update(fuel_type=""),
    )
    changed("missing_seats", lambda value: value["spec"].update(seats=None))
    changed(
        "missing_cargo",
        lambda value: value["spec"].update(cargo_volume_liters=None),
    )
    changed(
        "missing_liquid_consumption",
        lambda value: value["spec"].update(consumption_l_100km=None),
    )
    changed(
        "unsupported_fuel_type",
        lambda value: value["spec"].update(fuel_type="hydrogen"),
    )
    changed(
        "unsupported_body_style",
        lambda value: value["spec"].update(body_style="roadster"),
    )

    ev_missing_consumption = candidate(
        400,
        fuel_type="electric",
        consumption=None,
        electric_consumption=None,
        ev_range=350,
    )
    ev_missing_range = candidate(
        401,
        fuel_type="electric",
        consumption=None,
        electric_consumption=18,
        ev_range=None,
    )
    cases.extend(
        [
            ("missing_ev_consumption", ev_missing_consumption),
            ("missing_ev_range", ev_missing_range),
        ]
    )

    result = score_recommendations(
        AdvisorRecommendationRequest(
            budget_max_eur=30_000,
            primary_use="highway",
        ),
        [value for _, value in cases],
        as_of=AS_OF,
    )

    assert result.items == []
    assert result.excluded_counts_by_reason == {
        reason: 1 for reason, _ in cases
    }


def test_phev_is_not_excluded_as_unsupported():
    phev = candidate(499, fuel_type="plug_in_hybrid_petrol")
    result = score_recommendations(
        AdvisorRecommendationRequest(budget_max_eur=30_000, primary_use="city"),
        [phev],
        as_of=AS_OF,
    )
    assert result.items
    assert "unsupported_phev" not in result.excluded_counts_by_reason


def test_highway_ev_under_250_km_is_not_excluded_for_range():
    ev = candidate(
        498,
        fuel_type="electric",
        consumption=None,
        electric_consumption=18,
        ev_range=249,
    )
    result = score_recommendations(
        AdvisorRecommendationRequest(budget_max_eur=30_000, primary_use="highway"),
        [ev],
        as_of=AS_OF,
    )
    assert result.items
    assert "insufficient_highway_ev_range" not in result.excluded_counts_by_reason


def test_gold_12_rank_then_family_dedupe_is_permutation_stable_with_exact_tie_key():
    tied = [
        candidate(10, make="Alpha", model="Able", model_family_key="family-a"),
        candidate(11, make="Alpha", model="Able", model_family_key="family-a"),
        candidate(12, make="Alpha", model="Beta", model_family_key="family-b"),
        candidate(13, make="Bravo", model="Able", model_family_key="family-c"),
        candidate(14, make="Bravo", model="Beta", model_family_key="family-d"),
        candidate(15, make="Charlie", model="Able", model_family_key="family-e"),
        candidate(16, make="Delta", model="Able", model_family_key="family-f"),
    ]
    tied[0]["offer"]["mileage"] = 99_000
    tied[0]["vehicle"]["model_year"] = 2020
    tied[0]["spec"]["variant_key"] = "zzz"
    tied[0]["offer"]["listing_ref"] = "zzz"
    tied[1]["offer"]["mileage"] = 1
    tied[1]["vehicle"]["model_year"] = 2026
    tied[1]["spec"]["variant_key"] = "aaa"
    tied[1]["offer"]["listing_ref"] = "aaa"

    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
        condition="used",
    )
    expected_offer_ids = [
        str(tied[0]["offer"]["id"]),
        str(tied[2]["offer"]["id"]),
        str(tied[3]["offer"]["id"]),
        str(tied[4]["offer"]["id"]),
        str(tied[5]["offer"]["id"]),
    ]

    for permutation in (tied, list(reversed(tied)), tied[::2] + tied[1::2]):
        result = score_recommendations(request, permutation, as_of=AS_OF)
        assert [str(item.offer.id) for item in result.items] == expected_offer_ids
        assert len(result.items) == 5


def test_request_rejects_removed_priorities_and_duplicates():
    with pytest.raises(ValidationError):
        AdvisorRecommendationRequest(
            budget_max_eur=20_000,
            primary_use="city",
            priorities=["reliability"],
        )
    with pytest.raises(ValidationError):
        AdvisorRecommendationRequest(
            budget_max_eur=20_000,
            primary_use="city",
            priorities=["price", "price"],
        )
