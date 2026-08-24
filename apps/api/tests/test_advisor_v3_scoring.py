from datetime import datetime, timezone

from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.confidence import decision_confidence
from app.services.advisor.scoring import score_recommendations

from test_advisor_scoring import candidate


AS_OF = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)


def complete_candidate(index: int = 1):
    result = candidate(index, condition="new", mileage=None, price_eur=18_000)
    result["decision_context"] = {
        "dimensions": {
            "length_mm": 4200,
            "body_width_mm": 1800,
            "height_mm": 1600,
            "width_mirrors_folded_mm": 1700,
        },
        "safety": {"ratings": [{"overall_stars": 4}]},
        "vehicle_dna": {
            "comfort": {"value": 80},
            "sport": {"value": 80},
            "travel": {"value": 80},
            "technology": {"value": 80},
        },
        "reliability_assessment": {"value": 80},
    }
    return result


def score_one(candidate_data, priorities):
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
        priorities=priorities,
        annual_km=15_000,
    )
    return score_recommendations(request, [candidate_data], as_of=AS_OF).items[0]


def test_v3_exposes_structural_preference_and_composed_scores():
    item = score_one(
        complete_candidate(),
        priorities=["reliability", "running_cost", "comfort"],
    )
    assert item.structural_fit is not None
    assert item.preference_fit is not None
    assert item.decision_score == round(
        item.structural_fit * 0.65 + item.preference_fit * 0.35, 1
    )
    assert item.score == item.decision_score


def test_priority_order_does_not_change_structural_fit():
    first_candidate = complete_candidate(1)
    second_candidate = complete_candidate(2)
    for value in (first_candidate, second_candidate):
        value["decision_context"]["safety"]["ratings"][0]["overall_stars"] = 5
        value["decision_context"]["vehicle_dna"]["comfort"]["value"] = 70
        value["decision_context"]["vehicle_dna"]["technology"]["value"] = 80
    first = score_one(first_candidate, priorities=["safety", "technology", "comfort"])
    second = score_one(second_candidate, priorities=["comfort", "technology", "safety"])
    assert first.structural_fit == second.structural_fit
    assert first.preference_fit != second.preference_fit


def test_missing_preference_returns_provisional_legacy_score():
    missing = complete_candidate()
    missing["decision_context"].pop("reliability_assessment")
    item = score_one(
        missing, priorities=["reliability"]
    )
    assert item.decision_status == "insufficient_data"
    assert item.decision_score is None
    assert item.score == item.structural_fit
    assert "reliability" in item.missing_factors


def test_decision_confidence_uses_documented_weights_and_clamps_value():
    result = decision_confidence(
        profile_completeness=100,
        evidence_completeness=80,
        ranking_stability=50,
    )
    assert result.version == "decision-confidence-v1"
    assert result.value == 83.0
    assert result.details == {
        "profile_completeness": 100,
        "evidence_completeness": 80,
        "ranking_stability": 50,
    }


def test_module_failure_is_insufficient_data_without_neutral_score(monkeypatch):
    def fail(_candidate):
        raise RuntimeError("controlled")

    monkeypatch.setattr("app.services.advisor.scoring.assess_reliability", fail)
    item = score_one(complete_candidate(), priorities=["reliability"])
    assert item.decision_status == "insufficient_data"
    assert item.decision_score is None
    assert "reliability" in item.missing_factors
    assert item.evidence["assessments"]["reliability"]["value"] is None
