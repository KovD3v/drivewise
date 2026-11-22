from datetime import datetime, timezone

from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.confidence import decision_confidence
from app.services.advisor.decision import ModuleAssessment
from app.services.advisor.scoring import score_recommendations
from app.services.advisor import scoring as scoring_module

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


def score_one(candidate_data, priorities, **request_updates):
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
        priorities=priorities,
        annual_km=15_000,
        **request_updates,
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


def test_constraint_insufficient_data_forces_provisional_result():
    candidate_data = complete_candidate()
    request_garage = {
        "useful_length_mm": 5000,
        "useful_width_mm": 2500,
        "useful_height_mm": 2200,
        "door_width_mm": 2200,
        "door_height_mm": 2000,
    }
    candidate_data["decision_context"]["dimensions"].pop("width_mirrors_folded_mm")
    item = score_one(
        candidate_data,
        priorities=["price"],
        garage=request_garage,
        constraint_modes={"garage": "hard"},
    )
    assert item.decision_status == "insufficient_data"
    assert item.decision_score is None
    assert item.score == item.structural_fit
    assert "vehicle.width_mirrors_folded_mm" in item.missing_factors


def test_garage_assessment_runs_once_and_failure_is_provisional(monkeypatch):
    calls = 0

    def fail(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("controlled garage failure")

    monkeypatch.setattr(scoring_module, "garage_fit", fail)
    item = score_one(
        complete_candidate(),
        priorities=["price"],
        garage={
            "useful_length_mm": 5000,
            "useful_width_mm": 2500,
            "useful_height_mm": 2200,
            "door_width_mm": 2200,
            "door_height_mm": 2000,
        },
        constraint_modes={"garage": "hard"},
    )
    assert calls == 1
    assert item.decision_status == "insufficient_data"
    assert item.decision_score is None
    assert "module_error:RuntimeError" in item.evidence["missing_data"]


def test_unknown_specialist_applicability_is_missing_data_and_lowers_confidence():
    unknown = complete_candidate(801)
    unknown["decision_context"]["known_issues"] = [
        {"applicability": "unknown"}
    ]
    unknown["decision_context"]["recalls"] = [
        {"applicability": "unknown", "status": "open"}
    ]
    confirmed = complete_candidate(802)
    confirmed["decision_context"]["known_issues"] = [
        {"applicability": "not_applicable"}
    ]
    confirmed["decision_context"]["recalls"] = [
        {"applicability": "not_applicable", "status": "closed"}
    ]

    unknown_item = score_one(unknown, priorities=["price"])
    confirmed_item = score_one(confirmed, priorities=["price"])

    assert "issue_applicability" in unknown_item.missing_factors
    assert "recall_applicability" in unknown_item.missing_factors
    assert "issue_applicability" in unknown_item.warnings
    assert "recall_applicability" in unknown_item.warnings
    assert unknown_item.decision_confidence < confirmed_item.decision_confidence
    assert unknown_item.penalties == []
    assert confirmed_item.warnings == []


def test_ranking_stability_has_no_invented_single_or_tie_signal():
    one = score_one(complete_candidate(), priorities=["price"])
    assert one.evidence["ranking_stability"] == 0
    assert one.evidence["ranking_comparison"] == "none"

    first = complete_candidate(1)
    second = complete_candidate(2)
    tied = score_recommendations(
        AdvisorRecommendationRequest(
            budget_max_eur=20_000,
            primary_use="city",
            priorities=["price"],
            annual_km=15_000,
        ),
        [first, second],
        as_of=AS_OF,
    ).items
    assert all(item.evidence["ranking_stability"] == 0 for item in tied)
    assert all(item.evidence["ranking_comparison"] == "within_group_gap" for item in tied)

    separated_candidate = complete_candidate(3)
    separated_candidate["offer"]["price_eur"] = 19_000
    separated = score_recommendations(
        AdvisorRecommendationRequest(
            budget_max_eur=20_000,
            primary_use="city",
            priorities=["price"],
            annual_km=15_000,
        ),
        [first, separated_candidate],
        as_of=AS_OF,
    ).items
    assert separated[0].evidence["ranking_stability"] > 0


def test_exact_composition_gold_uses_stubbed_assessments(monkeypatch):
    candidate_data = complete_candidate()
    candidate_data["offer"]["price_eur"] = 19_444.444444
    candidate_data["spec"]["consumption_l_100km"] = 7.6666667 / 1.91662
    candidate_data["decision_context"]["vehicle_dna"] = {
        "city": {"value": 80},
        "comfort": {"value": 90},
        "sport": {"value": 70},
        "travel": {"value": 71.3333333},
        "technology": {"value": 80},
    }
    monkeypatch.setattr(
        scoring_module,
        "estimate_tco",
        lambda *args, **kwargs: ModuleAssessment(
            status="estimated", version="tco-v1", value=4923.809524, assumptions=("stub",)
        ),
    )
    monkeypatch.setattr(
        scoring_module,
        "assess_reliability",
        lambda _candidate: ModuleAssessment(status="available", version="reliability-v1", value=90),
    )
    monkeypatch.setattr(
        scoring_module,
        "assess_safety",
        lambda _candidate: ModuleAssessment(status="available", version="safety-v1", value=66.190476),
    )
    monkeypatch.setattr(
        scoring_module,
        "powertrain_fit",
        lambda *args, **kwargs: ModuleAssessment(status="available", version="powertrain-fit-v1", value=80),
    )
    monkeypatch.setattr(
        scoring_module,
        "family_fit",
        lambda *args, **kwargs: ModuleAssessment(status="available", version="family-fit-v1", value=80),
    )
    item = score_one(
        candidate_data,
        priorities=["reliability", "running_cost", "comfort"],
    )
    assert item.structural_fit == 80.0
    assert item.preference_fit == 90.0
    assert item.decision_score == 83.5
    assert item.score == item.decision_score


def test_priority_metric_mapping_is_complete():
    assert set(scoring_module.PRIORITY_METRIC) == {
        "price", "budget", "running_cost", "space", "family", "reliability",
        "safety", "comfort", "performance", "technology", "efficiency_range",
        "powertrain_fit",
    }


def test_penalties_are_ordered_and_capped_before_composition():
    candidate_data = complete_candidate()
    candidate_data["decision_context"]["known_issues"] = [
        {"applicability": "applicable", "severity": "critical", "penalty": 20}
    ]
    candidate_data["decision_context"]["recalls"] = [
        {"applicability": "applicable", "status": "open", "penalty": 20}
    ]
    item = score_one(candidate_data, priorities=["price"])
    assert item.penalties == ["known_issue_penalty:8", "recall_penalty:6"]
    assert item.structural_fit <= 100 - 14
