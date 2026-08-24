from dataclasses import fields

import pytest

from app.schemas.advisor import AdvisorRecommendationRequest
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
    from app.schemas.advisor import AdvisorRecommendationResponse

    names = {field.name for field in fields(ModuleAssessment)}
    assert names >= {"status", "version", "value", "details", "missing_data"}
    response_fields = AdvisorRecommendationResponse.model_fields
    assert response_fields["decision_status"].default == "insufficient_data"
    assert response_fields["decision_score"].default is None
