from dataclasses import fields
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from app.schemas.advisor import AdvisorRecommendationRequest, AdvisorRecommendationResponse
from app.schemas.guided_decisions import DecisionProfile
from app.services.advisor.decision import ModuleAssessment
from app.services.advisor.energy_prices import (
    ELECTRICITY_PRICE_EUR_PER_KWH,
    ENERGY_ASSUMPTION_VERSION,
    LIQUID_ENERGY_PRICES_EUR_PER_LITER,
)
from app.services.advisor.tco import estimate_tco
from app.services.advisor.constraints import evaluate_constraints
from app.services.advisor.garage import family_fit, garage_fit
from app.services.advisor.powertrain import powertrain_fit


AS_OF = datetime(2026, 8, 25, tzinfo=timezone.utc)


def v3_request(**kwargs):
    return AdvisorRecommendationRequest(
        budget_max_eur=30_000,
        primary_use="family",
        annual_km=kwargs.pop("annual_km", 15_000),
        **kwargs,
    )


@pytest.fixture
def candidate():
    return {
        "vehicle": {"id": UUID("00000000-0000-4000-8000-000000000001"), "model_year": 2022},
        "spec": {
            "body_style": "hatchback",
            "fuel_type": "petrol",
            "consumption_l_100km": 5.0,
            "power_kw": 96.0,
        },
        "offer": {"price_eur": 20_000.0, "condition": "used", "mileage": 40_000},
    }


def test_tco_returns_a_versioned_full_estimate(candidate):
    result = estimate_tco(v3_request(), candidate, as_of=AS_OF)
    assert result.status == "estimated"
    assert result.version == "tco-v1"
    annual = result.details["annual_eur"]
    assert set(annual) == {
        "energy", "insurance", "tax", "maintenance",
        "tyres", "depreciation", "total",
    }
    assert annual["total"] == sum(value for key, value in annual.items() if key != "total")
    assert result.assumptions


@pytest.mark.parametrize(
    "fuel_type",
    [
        "petrol", "diesel", "mild_hybrid_petrol", "full_hybrid_petrol",
        "plug_in_hybrid_petrol", "electric", "petrol_lpg",
    ],
)
def test_powertrains_are_assessed_not_legacy_excluded(fuel_type, candidate):
    candidate["spec"]["fuel_type"] = fuel_type
    if fuel_type == "electric":
        candidate["spec"].update(
            energy_consumption_kwh_100km=18, wltp_range_km=350
        )
    if fuel_type == "plug_in_hybrid_petrol":
        candidate["spec"].update(
            energy_consumption_kwh_100km=18, wltp_range_km=60
        )
        candidate["decision_context"] = {"charging_context": {"home": True}}
    result = powertrain_fit(v3_request(), candidate)
    assert result.status in {"available", "estimated", "insufficient_data"}
    assert result.version == "powertrain-fit-v1"


def test_request_accepts_plug_in_hybrid_fuel_type():
    request = v3_request(preferred_fuel_type="plug_in_hybrid_petrol")
    assert request.preferred_fuel_type == "plug_in_hybrid_petrol"


def test_tco_fails_closed_without_consumption(candidate):
    candidate["spec"]["consumption_l_100km"] = None
    result = estimate_tco(v3_request(), candidate, as_of=AS_OF)
    assert result.status == "insufficient_data"
    assert "consumption" in result.missing_data


def test_tco_omits_missing_non_energy_component(candidate):
    candidate["spec"]["power_kw"] = None
    result = estimate_tco(v3_request(), candidate, as_of=AS_OF)
    assert result.status == "estimated"
    assert "tax" in result.missing_data
    assert "tax" not in result.details["annual_eur"]


def test_tco_rounds_components_and_total_to_decimal_cents(candidate):
    candidate["offer"]["price_eur"] = 19_999.99
    candidate["spec"]["consumption_l_100km"] = 5.123
    annual = estimate_tco(
        v3_request(annual_km=12_345), candidate, as_of=AS_OF
    ).details["annual_eur"]
    assert all(value == round(value, 2) for value in annual.values())
    assert Decimal(str(annual["total"])) == sum(
        (Decimal(str(value)) for key, value in annual.items() if key != "total"),
        Decimal("0.00"),
    )


def test_tco_assumptions_name_reproducible_v1_constants(candidate):
    assumptions = estimate_tco(v3_request(), candidate, as_of=AS_OF).assumptions
    text = " ".join(assumptions)
    for required in (
        "EUR 650",
        "0.8%",
        "EUR 1,600",
        "EUR 2.58/kW through 100 kW",
        "EUR 3.87/kW above 100 kW",
        "100 kW cap",
        "9.333%",
        "city_car/small_hatchback EUR 180",
        "hatchback/sedan/wagon EUR 240",
        "crossover/SUV/MPV/van EUR 300",
        "maintenance-v1",
        "it-energy-2026-07-16-v1",
    ):
        assert required in text


def test_tco_assumptions_name_energy_formula_rates_and_version(candidate):
    text = " ".join(estimate_tco(v3_request(), candidate, as_of=AS_OF).assumptions)
    assert "consumption × rate × annual_km ÷ 100" in text
    assert ENERGY_ASSUMPTION_VERSION in text
    for fuel_type, rate in LIQUID_ENERGY_PRICES_EUR_PER_LITER.items():
        assert f"{fuel_type} EUR {rate:.5f}/L" in text
    assert f"electricity EUR {ELECTRICITY_PRICE_EUR_PER_KWH:.5f}/kWh" in text


def test_v2_request_defaults_to_single_usage_and_soft_preferences():
    request = AdvisorRecommendationRequest(
        budget_max_eur=30_000,
        primary_use="family",
        preferred_body_style="suv",
    )
    assert request.usage == ["family"]
    assert request.constraint_modes.body_style == "soft"


def test_insufficient_assessment_rejects_a_value():
    with pytest.raises(ValueError):
        ModuleAssessment(
            status="insufficient_data",
            version="reliability-v1",
            value=70,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"version": "", "assumptions": ("catalog estimate",)},
        {"version": "reliability-v1", "assumptions": ()},
    ],
)
def test_estimated_assessment_requires_version_and_named_assumption(kwargs):
    with pytest.raises(ValueError):
        ModuleAssessment(status="estimated", value=70, **kwargs)


def test_v3_assessment_contract_has_explicit_missing_data_state():
    assessment = ModuleAssessment(
        status="insufficient_data",
        version="reliability-v1",
        missing_data=("service_history",),
    )
    assert assessment.value is None
    assert assessment.missing_data == ("service_history",)


def test_v2_request_rejects_duplicate_usage():
    with pytest.raises(ValueError):
        AdvisorRecommendationRequest(
            budget_max_eur=30_000,
            primary_use="family",
            usage=["family", "family"],
        )


def test_recommendation_response_keeps_v2_shape_with_v3_defaults():
    names = {field.name for field in fields(ModuleAssessment)}
    assert names >= {"status", "version", "value", "details", "missing_data"}
    response_fields = AdvisorRecommendationResponse.model_fields
    assert response_fields["decision_status"].default == "insufficient_data"
    assert response_fields["decision_score"].default is None


def test_guided_constraint_modes_use_camel_case_wire_aliases():
    profile = DecisionProfile.model_validate(
        {"constraintModes": {"bodyStyle": "hard", "fuelType": "hard"}}
    )
    assert profile.model_dump(by_alias=True)["constraintModes"] == {
        "budget": "soft",
        "bodyStyle": "hard",
        "fuelType": "hard",
        "transmission": "soft",
        "garage": "soft",
    }


def test_recommendation_response_rejects_unknown_decision_status():
    with pytest.raises(ValueError):
        AdvisorRecommendationResponse(
            run_id="50000000-0000-4000-8000-000000000001",
            scoring_version="advisor-v2.0",
            assumptions=[],
            excluded_counts_by_reason={},
            groups=[],
            decision_status="estimated",
        )


def test_passenger_constraint_excludes_insufficient_seats(candidate):
    candidate["spec"]["seats"] = 4
    result = evaluate_constraints(v3_request(passengers_usual=5), candidate)
    assert result.status == "excluded"
    assert result.reasons == ("insufficient_seats",)


def test_family_fit_uses_versioned_cargo_target(candidate):
    result = family_fit(children_count=2, passengers_usual=4, candidate=candidate)
    assert result.version == "family-fit-v1"
    assert result.details["cargo_target_liters"] == 400


def test_garage_fit_fails_closed_without_folded_width(candidate):
    garage = {
        "useful_length_mm": 5000,
        "useful_width_mm": 2500,
        "useful_height_mm": 2200,
        "door_width_mm": 2200,
        "door_height_mm": 2000,
    }
    candidate["decision_context"] = {
        "dimensions": {"length_mm": 4200, "body_width_mm": 1800, "height_mm": 1600}
    }
    result = garage_fit(garage, candidate)
    assert result.status == "insufficient_data"
    assert "vehicle.width_mirrors_folded_mm" in result.missing_data


def test_garage_fit_compares_body_and_folded_mirror_width_separately(candidate):
    garage = {
        "useful_length_mm": 5000,
        "useful_width_mm": 2500,
        "useful_height_mm": 2200,
        "door_width_mm": 2200,
        "door_height_mm": 2000,
    }
    candidate["decision_context"] = {
        "dimensions": {
            "length_mm": 4200,
            "body_width_mm": 1800,
            "width_mirrors_folded_mm": 2100,
            "height_mm": 1600,
        }
    }
    result = garage_fit(garage, candidate)
    assert result.status == "available"
    assert result.details["margins"]["width_mm"] == 700
    assert result.details["margins"]["door_width_mm"] == 100


@pytest.mark.parametrize(
    ("price", "mode", "status", "reasons", "tradeoffs"),
    [
        (19_999, "soft", "excluded", ("below_budget_min",), ()),
        (30_000, "soft", "eligible", (), ()),
        (30_001, "soft", "eligible", (), ("above_budget",)),
        (33_000, "soft", "eligible", (), ("above_budget",)),
        (33_001, "soft", "excluded", ("above_budget_tolerance",), ()),
        (30_001, "hard", "excluded", ("above_budget",), ()),
    ],
)
def test_budget_boundaries_preserve_v2_and_hard_modes(
    candidate, price, mode, status, reasons, tradeoffs
):
    candidate["offer"]["price_eur"] = price
    request = v3_request(
        budget_min_eur=20_000,
        constraint_modes={"budget": mode},
    )
    result = evaluate_constraints(request, candidate)
    assert result.status == status
    assert result.reasons == reasons
    assert result.soft_tradeoffs == tradeoffs


def test_family_fit_none_children_uses_baseline_and_missing_cargo_is_insufficient(candidate):
    candidate["spec"]["cargo_volume_liters"] = None
    result = family_fit(children_count=None, passengers_usual=None, candidate=candidate)
    assert result.status == "insufficient_data"
    assert result.details["cargo_target_liters"] == 250
    assert result.missing_data == ("vehicle.cargo_volume_liters",)


def test_family_fit_caps_target_and_requires_seats_only_for_passengers(candidate):
    candidate["spec"].update({"cargo_volume_liters": 600, "seats": None})
    result = family_fit(children_count=10, passengers_usual=None, candidate=candidate)
    assert result.status == "available"
    assert result.details["cargo_target_liters"] == 550
    result = family_fit(children_count=0, passengers_usual=4, candidate=candidate)
    assert result.status == "insufficient_data"
    assert result.missing_data == ("vehicle.seats",)


def test_request_accepts_typed_garage_dimensions():
    request = v3_request(
        garage={
            "useful_length_mm": 5000,
            "useful_width_mm": 2500,
            "useful_height_mm": 2200,
            "door_width_mm": 2200,
            "door_height_mm": 2000,
        }
    )
    assert request.garage.useful_width_mm == 2500


def test_garage_mode_controls_incompatible_result(candidate):
    candidate["decision_context"] = {
        "dimensions": {
            "length_mm": 5200,
            "body_width_mm": 2600,
            "width_mirrors_folded_mm": 2700,
            "height_mm": 1600,
        }
    }
    garage = {
        "useful_length_mm": 5000,
        "useful_width_mm": 2500,
        "useful_height_mm": 2200,
        "door_width_mm": 2200,
        "door_height_mm": 2000,
    }
    soft = evaluate_constraints(v3_request(garage=garage), candidate)
    assert soft.status == "eligible"
    assert soft.soft_tradeoffs == ("garage_incompatible",)
    hard = evaluate_constraints(
        v3_request(garage=garage, constraint_modes={"garage": "hard"}), candidate
    )
    assert hard.status == "excluded"
    assert hard.reasons == ("garage_incompatible",)


def test_hard_garage_missing_folded_width_is_insufficient_data(candidate):
    candidate["decision_context"] = {
        "dimensions": {"length_mm": 4200, "body_width_mm": 1800, "height_mm": 1600}
    }
    garage = {
        "useful_length_mm": 5000,
        "useful_width_mm": 2500,
        "useful_height_mm": 2200,
        "door_width_mm": 2200,
        "door_height_mm": 2000,
    }
    result = evaluate_constraints(
        v3_request(garage=garage, constraint_modes={"garage": "hard"}), candidate
    )
    assert result.status == "insufficient_data"
    assert "vehicle.width_mirrors_folded_mm" in result.missing_data
