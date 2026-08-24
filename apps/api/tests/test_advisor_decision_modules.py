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
