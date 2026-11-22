import pytest

from app.services.advisor.issues import known_issue_penalty
from app.services.advisor.recalls import recall_penalty
from app.services.advisor.reliability import assess_reliability
from app.services.advisor.safety import assess_safety
from app.services.advisor.vehicle_dna import assess_vehicle_dna


@pytest.fixture
def candidate():
    return {
        "vehicle": {"model_year": 2022},
        "spec": {"variant_key": "style-1"},
        "decision_context": {
            "identity": {"generation_name": "gen-4"},
            "powertrain": {"engine_code": "E1", "transmission_type": "manual"},
            "safety": {"ratings": [{"assessment_system": "Euro NCAP", "overall_stars": 5, "adult_occupant_percent": 88}]},
        },
    }


def test_safety_uses_ratings_and_provenance(candidate):
    result = assess_safety(candidate)
    assert result.status == "available"
    assert result.version == "safety-v1"
    assert 0 <= result.value <= 100
    assert result.evidence


@pytest.mark.parametrize("field,value", [("adult_occupant_percent", -1), ("adult_occupant_percent", 101), ("overall_stars", 6), ("overall_stars", -1)])
def test_safety_rejects_invalid_rating_domains(candidate, field, value):
    candidate["decision_context"]["safety"]["ratings"] = [{field: value}]
    result = assess_safety(candidate)
    assert result.status == "insufficient_data"
    assert "invalid_safety_rating" in result.missing_data


def test_reliability_without_input_is_insufficient(candidate):
    result = assess_reliability(candidate)
    assert result.status == "insufficient_data"
    assert result.missing_data == ("reliability_assessment",)


def test_vehicle_dna_without_input_is_insufficient(candidate):
    result = assess_vehicle_dna(candidate)
    assert set(result) == {"comfort", "sport", "travel", "technology"}
    assert all(value.status == "insufficient_data" for value in result.values())


def test_issue_penalizes_only_matching_variant(candidate):
    assert known_issue_penalty(candidate, [{"engine_code": "OTHER"}]).value == 0
    engine_code = candidate["decision_context"]["powertrain"]["engine_code"]
    assert known_issue_penalty(candidate, [{"engine_code": engine_code, "severity": "high"}]).value > 0


def test_issue_production_year_bounds_are_inclusive_and_missing_year_is_unknown(candidate):
    issue = {"production_year_min": 2022, "production_year_max": 2022, "severity": "high"}
    assert known_issue_penalty(candidate, [issue]).value > 0
    candidate["vehicle"]["model_year"] = 2023
    assert known_issue_penalty(candidate, [issue]).value == 0
    candidate["vehicle"].pop("model_year")
    result = known_issue_penalty(candidate, [issue])
    assert result.value == 0 and "issue_applicability" in result.missing_data


def test_explicit_non_applicable_states_do_not_warn_or_penalize(candidate):
    issue = {"applicability": "mismatched", "severity": "critical"}
    result = known_issue_penalty(candidate, [issue])
    assert result.value == 0 and not result.missing_data


def test_unknown_recall_applicability_warns_without_penalty(candidate):
    result = recall_penalty(candidate, [{"applicability": "unknown", "status": "open"}])
    assert result.value == 0
    assert "recall_applicability" in result.missing_data


def test_open_recall_is_capped_and_resolved_is_visible_without_penalty(candidate):
    result = recall_penalty(candidate, [{"applicability": "applicable", "status": "open", "penalty": 20}])
    assert result.value == 6
    resolved = recall_penalty(candidate, [{"applicability": "applicable", "status": "resolved"}])
    assert resolved.value == 0 and resolved.evidence


def test_recall_unknown_status_fails_closed(candidate):
    result = recall_penalty(candidate, [{"applicability": "applicable"}])
    assert result.value == 0 and "recall_status" in result.missing_data
