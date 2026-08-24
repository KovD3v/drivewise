from dataclasses import fields

import pytest

from app.schemas.advisor import AdvisorRecommendationRequest, AdvisorRecommendationResponse
from app.schemas.guided_decisions import DecisionProfile
from app.services.advisor.decision import ModuleAssessment


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
