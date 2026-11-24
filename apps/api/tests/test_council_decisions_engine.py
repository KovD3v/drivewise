"""Regression tests for the Architectural Council fixes on guided decisions.

C1: a reopened decision recomputes its ranking live; turns are capped.
H1/L5: the free-text interpreter stays linear and never crashes on numbers.
Garage: a demonstrated misfit is incompatible even with a missing dimension,
and a hard garage constraint is never dropped while measures are missing.
D1/D3: Advisor prose is Italian while every structured field stays the same.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies import (
    get_advisor_repository,
    get_guided_decisions_repository,
)
from app.api.routers.advisor import get_advisor_clock
from app.api.routers.guided_decisions import get_guided_decision_clock
from app.main import app
from app.schemas.advisor import AdvisorConstraintModes, AdvisorRecommendationRequest
from app.schemas.guided_decisions import DecisionFact, DecisionProfile, GarageProfile
from app.services.advisor import messages_it
from app.services.advisor.garage import garage_fit
from app.services.advisor.scoring import build_assumptions, score_recommendations
from app.services.guided_decisions.engine import (
    MAX_GUIDED_DECISION_TURNS,
    RECOMPUTE_FALLBACK_WARNING,
    process_guided_decision_turn,
)
from app.services.guided_decisions.garage import (
    VehicleDimensions,
    evaluate_garage_compatibility,
)
from app.services.guided_decisions.interpreter import extract_profile_updates
from app.services.guided_decisions.questions import QUESTION_DEFINITIONS
from test_advisor_scoring import candidate as scoring_candidate
from test_guided_decisions import (
    CandidateAdvisorRepository,
    EmptyAdvisorRepository,
    InMemoryGuidedDecisionsRepository,
)


AS_OF = datetime(2026, 8, 12, 10, tzinfo=timezone.utc)
DECISION_ID = UUID("60000000-0000-4000-8000-0000000000c1")
VEHICLE_ID = UUID("00000000-0000-4000-8000-0000000000c1")
SPEC_ID = UUID("20000000-0000-4000-8000-0000000000c1")
DIMENSIONS = {
    "length_mm": 4_200,
    "body_width_mm": 1_800,
    "height_mm": 1_600,
    "width_mirrors_folded_mm": 1_700,
}


def _fact(value):
    return DecisionFact(
        value=value, confidence=1, source="user", confirmed=True, updated_at=AS_OF
    )


def _extract(message: str, expected_question_id: str | None = None, profile=None):
    return extract_profile_updates(
        message,
        profile or DecisionProfile(),
        expected_question_id=expected_question_id,
        captured_at=AS_OF,
    )


def _ready_profile(**overrides) -> DecisionProfile:
    """A profile that unblocks the preview, so the Advisor request is built."""
    values = {
        "budget_eur": _fact(30_000),
        "primary_use": _fact("city"),
        "annual_km": _fact(15_000),
        **overrides,
    }
    return DecisionProfile(**values)


class DimensionedAdvisorRepository(EmptyAdvisorRepository):
    def list_candidates(self, *, as_of):
        self.calls.append(("list", as_of))
        candidate = scoring_candidate(1)
        candidate["decision_context"] = {"dimensions": dict(DIMENSIONS)}
        return [candidate]


class SwappableAdvisorRepository(EmptyAdvisorRepository):
    def __init__(self) -> None:
        super().__init__()
        self.candidates = [scoring_candidate(1)]

    def list_candidates(self, *, as_of):
        self.calls.append(("list", as_of))
        return list(self.candidates)


@pytest.fixture
def guided_api():
    decisions = InMemoryGuidedDecisionsRepository()
    advisor = SwappableAdvisorRepository()
    app.dependency_overrides[get_guided_decisions_repository] = lambda: decisions
    app.dependency_overrides[get_advisor_repository] = lambda: advisor
    app.dependency_overrides[get_guided_decision_clock] = lambda: AS_OF
    app.dependency_overrides[get_advisor_clock] = lambda: AS_OF
    yield TestClient(app), decisions, advisor
    app.dependency_overrides.clear()


# --- C1: live recompute and turn cap -------------------------------------


def _create(client) -> str:
    created = client.post(
        "/guided-decisions",
        json={"message": "Cerco una city car usata, budget 30.000 euro, per la citta"},
    )
    assert created.status_code == 200
    return created.json()["decisionId"]


def test_reopened_decision_drops_candidates_removed_from_the_catalogue(guided_api):
    client, _decisions, advisor = guided_api
    decision_id = _create(client)
    first = client.get(f"/guided-decisions/{decision_id}").json()
    assert any(group["items"] for group in first["previewRanking"]["groups"])

    # A revoked source disappears from list_candidates; the reopened link
    # must follow the catalogue, not the stored answer.
    advisor.candidates = []
    reopened = client.get(f"/guided-decisions/{decision_id}")

    assert reopened.status_code == 200
    payload = reopened.json()
    assert payload["previewRanking"]["status"] == "insufficient_inventory"
    assert all(not group["items"] for group in payload["previewRanking"]["groups"])
    assert payload["profileVersion"] == 1
    assert payload["message"] == first["message"]


def test_reopened_decision_falls_back_to_stored_answer_for_legacy_profile(guided_api):
    client, decisions, _advisor = guided_api
    decision_id = _create(client)
    stored_ranking = decisions.record.last_response["previewRanking"]
    # A legacy profile that today's Advisor validation rejects.
    legacy = decisions.record.decision_profile.model_copy(
        update={"passengers_usual": _fact(0)}
    )
    decisions.record = decisions.record.model_copy(update={"decision_profile": legacy})

    reopened = client.get(f"/guided-decisions/{decision_id}")

    assert reopened.status_code == 200
    payload = reopened.json()
    assert RECOMPUTE_FALLBACK_WARNING in payload["warnings"]
    assert payload["previewRanking"] == stored_ranking


def test_turns_are_capped_before_any_catalogue_query(guided_api):
    client, decisions, advisor = guided_api
    decision_id = _create(client)

    decisions.record = decisions.record.model_copy(
        update={"profile_version": MAX_GUIDED_DECISION_TURNS - 1}
    )
    allowed = client.post(
        f"/guided-decisions/{decision_id}/turns",
        json={
            "message": "15.000 km all'anno",
            "expectedProfileVersion": MAX_GUIDED_DECISION_TURNS - 1,
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["profileVersion"] == MAX_GUIDED_DECISION_TURNS

    calls_before = len(advisor.calls)
    capped = client.post(
        f"/guided-decisions/{decision_id}/turns",
        json={
            "message": "12.000 km all'anno",
            "expectedProfileVersion": MAX_GUIDED_DECISION_TURNS,
        },
    )
    assert capped.status_code == 409
    assert capped.json()["detail"] == {"code": "max_turns_reached"}
    assert len(advisor.calls) == calls_before


def test_preview_runs_a_single_catalogue_query():
    repository = CandidateAdvisorRepository()
    process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=2,
        current_profile=_ready_profile(),
        message="nuova",
        advisor_repository=repository,
        as_of=AS_OF,
    )
    assert repository.calls == [("list", AS_OF)]


# --- H1/L5: interpreter -----------------------------------------------------


ADVERSARIAL_PAYLOADS = {
    "digit_space_runs": "1" + " " * 1_990 + "x",
    "digits_and_spaces": "1 " * 1_000,
    "digits_and_tabs": "1\t\t" * 660,
    "dotted_digits": "1." * 999 + "x",
    "budget_then_digits": "budget " + "1 " * 995 + "x",
    "separators": ("9 ,'" * 500)[:2_000],
    "long_number": "9" * 2_000,
}


@pytest.mark.parametrize(
    "expected_question_id",
    [None, "budget_eur", "annual_km", "garage.useful_length_mm"],
)
@pytest.mark.parametrize("payload_name", sorted(ADVERSARIAL_PAYLOADS))
def test_interpreter_is_linear_on_two_kilobyte_adversarial_input(
    expected_question_id, payload_name
):
    message = ADVERSARIAL_PAYLOADS[payload_name][:2_000]
    durations = []
    for _ in range(3):
        started = time.perf_counter()
        _extract(message, expected_question_id)
        durations.append(time.perf_counter() - started)
    assert min(durations) < 0.05


@pytest.mark.parametrize(
    ("message", "expected_question_id"),
    [
        ("budget " + "9" * 40 + " euro", None),
        ("9" * 40, "budget_eur"),
        ("9" * 40, "garage.useful_height_mm"),
        ("9" * 40 + " passeggeri", None),
    ],
)
def test_numbers_beyond_decimal_precision_are_ignored(message, expected_question_id):
    profile, updated_fields = _extract(message, expected_question_id)
    assert updated_fields == []
    assert profile == DecisionProfile()


def test_long_number_is_not_read_as_one_of_its_slices():
    _profile, updated_fields = _extract("budget 1" + "0" * 30 + " euro")
    assert "budget_eur" not in updated_fields


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("budget 35.000 euro", 35_000),
        ("budget 35 mila", 35_000),
        ("35k euro", 35_000),
        ("fino a 20.000 €", 20_000),
    ],
)
def test_budget_amounts_still_parse(message, expected):
    profile, _ = _extract(message)
    assert profile.budget_eur.value == expected


def test_submitted_priority_order_is_preserved():
    profile, _ = _extract(
        "price space running_cost efficiency_range", "priorities"
    )
    assert profile.priorities.value == [
        "price",
        "space",
        "running_cost",
        "efficiency_range",
    ]
    mixed, _ = _extract("price spazio", "priorities")
    assert mixed.priorities.value == ["price", "space"]


@pytest.mark.parametrize(
    "message", ["0 passeggeri", "siamo in 0", "99 figli", "0 persone"]
)
def test_out_of_range_counts_never_reach_the_advisor_request(message):
    result = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=2,
        current_profile=_ready_profile(),
        message=message,
        advisor_repository=CandidateAdvisorRepository(),
        as_of=AS_OF,
    )
    assert result.profile.passengers_usual is None
    assert result.profile.children_count is None
    assert result.response.preview_ranking.status != "blocked"


def test_budget_answer_with_distance_unit_is_rejected():
    profile, updated_fields = _extract("12.000 km", "budget_eur")
    assert updated_fields == []
    assert profile.budget_eur is None
    accepted, _ = _extract("12.000 euro", "budget_eur")
    assert accepted.budget_eur.value == 12_000


def test_annual_km_answer_keeps_its_unit():
    profile, _ = _extract("15.000 km", "annual_km")
    assert profile.annual_km.value == 15_000


@pytest.mark.parametrize(
    "message", ["ibrida plug-in", "plug in hybrid", "un ibrido ricaricabile", "phev"]
)
def test_plug_in_terms_win_over_generic_hybrid(message):
    profile, _ = _extract(message)
    assert profile.preferred_fuel_type.value == "plug_in_hybrid_petrol"


def test_plug_in_is_a_fuel_option():
    definition = next(
        item for item in QUESTION_DEFINITIONS if item.key == "preferred_fuel_type"
    )
    assert "plug_in_hybrid_petrol" in definition.question.constraints.options
    profile, _ = _extract("plug_in_hybrid_petrol", "preferred_fuel_type")
    assert profile.preferred_fuel_type.value == "plug_in_hybrid_petrol"
    generic, _ = _extract("ibrida")
    assert generic.preferred_fuel_type.value == "hybrid_petrol"


@pytest.mark.parametrize("literal", ["Infinity", "-Infinity", "NaN"])
def test_infinity_and_nan_are_rejected_at_validation_time(literal):
    with pytest.raises(ValidationError):
        AdvisorRecommendationRequest.model_validate_json(
            f'{{"budget_max_eur": {literal}, "primary_use": "city"}}'
        )


@pytest.mark.xfail(
    raises=ValueError,
    strict=False,
    reason=(
        "FastAPI's default 422 handler echoes the rejected inf input and "
        "json.dumps refuses it; the fix is a validation handler in app/main.py."
    ),
)
def test_infinity_over_http_returns_422(guided_api):
    client, _decisions, _advisor = guided_api
    response = client.post(
        "/advisor/recommendations",
        content=b'{"budget_max_eur": Infinity, "primary_use": "city"}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    nan = client.post(
        "/advisor/recommendations",
        content=b'{"budget_max_eur": NaN, "primary_use": "city"}',
        headers={"content-type": "application/json"},
    )
    assert nan.status_code == 422


# --- Garage ---------------------------------------------------------------


def _partial_garage_profile(**dimensions) -> DecisionProfile:
    return DecisionProfile(
        parking=_fact("garage"),
        garage=GarageProfile(**{key: _fact(value) for key, value in dimensions.items()}),
    )


def test_negative_margin_is_incompatible_even_with_a_missing_dimension():
    profile = _partial_garage_profile(
        useful_length_mm=4_000,
        useful_width_mm=2_300,
        useful_height_mm=2_100,
        door_height_mm=2_000,
    )
    check = evaluate_garage_compatibility(
        profile,
        vehicle_id=VEHICLE_ID,
        spec_id=SPEC_ID,
        vehicle_dimensions=VehicleDimensions(4_400, 1_850, 1_700, None),
    )
    assert check.status == "incompatible"
    assert check.margins.length_mm == -400
    assert check.margins.door_width_mm is None
    assert "garage.door_width_mm" in check.missing_data


def test_missing_dimension_without_a_misfit_stays_insufficient():
    profile = _partial_garage_profile(
        useful_length_mm=4_900, useful_width_mm=2_300, useful_height_mm=2_100
    )
    check = evaluate_garage_compatibility(
        profile,
        vehicle_id=VEHICLE_ID,
        spec_id=SPEC_ID,
        vehicle_dimensions=VehicleDimensions(4_400, 1_850, 1_700, 1_950),
    )
    assert check.status == "insufficient_data"
    assert check.missing_data == ["garage.door_width_mm", "garage.door_height_mm"]


def test_advisor_garage_fit_excludes_a_demonstrated_misfit():
    candidate = {"decision_context": {"dimensions": {**DIMENSIONS, "length_mm": 5_000}}}
    del candidate["decision_context"]["dimensions"]["width_mirrors_folded_mm"]
    misfit = garage_fit({"useful_length_mm": 4_500}, candidate)
    assert misfit.status == "available"
    assert misfit.value == 0.0
    assert misfit.details["margins"] == {"length_mm": -500}
    assert "vehicle.width_mirrors_folded_mm" in misfit.missing_data

    unknown = garage_fit({"useful_length_mm": 5_500}, candidate)
    assert unknown.status == "insufficient_data"


def _hard_garage_profile(**dimensions) -> DecisionProfile:
    return _ready_profile(
        parking=_fact("garage"),
        garage=GarageProfile(**{key: _fact(value) for key, value in dimensions.items()}),
        constraint_modes=AdvisorConstraintModes(garage="hard"),
    )


def _preview(profile: DecisionProfile):
    return process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=2,
        current_profile=profile,
        message="ok",
        advisor_repository=DimensionedAdvisorRepository(),
        as_of=AS_OF,
    ).response


def test_hard_garage_with_missing_measures_keeps_the_preview_provisional():
    response = _preview(_hard_garage_profile(useful_length_mm=4_900))

    items = [item for group in response.preview_ranking.groups for item in group.items]
    assert items
    assert response.preview_ranking.status == "provisional"
    assert all(item.decision_status == "insufficient_data" for item in items)
    assert all(item.decision_score is None for item in items)
    assert all("garage.door_height_mm" in item.missing_factors for item in items)
    assert {check.status for check in response.garage_compatibility} == {
        "insufficient_data"
    }


def test_hard_garage_excludes_a_vehicle_a_known_measure_rules_out():
    response = _preview(_hard_garage_profile(useful_length_mm=4_000))
    assert response.preview_ranking.status == "insufficient_inventory"


def test_soft_garage_with_missing_measures_is_unchanged():
    profile = _hard_garage_profile(useful_length_mm=4_900).model_copy(
        update={"constraint_modes": AdvisorConstraintModes()}
    )
    response = _preview(profile)
    items = [item for group in response.preview_ranking.groups for item in group.items]
    assert items
    assert all("garage.door_height_mm" not in item.missing_factors for item in items)


# --- D1/D3: Italian messages ------------------------------------------------


def test_assumptions_are_italian_and_quote_the_shared_energy_constants():
    request = AdvisorRecommendationRequest(budget_max_eur=20_000, primary_use="city")
    assumptions = build_assumptions(request)
    text = " ".join(assumptions)
    assert "Percorrenza annua" in text
    assert "1,91662 EUR/L" in text
    assert "0,29593 EUR/kWh" in text
    for english in ("Annual distance", "running_cost component", "Only the first"):
        assert english not in text


def test_soft_tradeoff_factor_keeps_its_code_and_speaks_italian():
    candidate = scoring_candidate(1)
    request = AdvisorRecommendationRequest(
        budget_max_eur=30_000,
        primary_use="city",
        preferred_fuel_type="diesel",
    )
    result = score_recommendations(request, [candidate], as_of=AS_OF)
    item = next(item for group in result.groups for item in group.items)
    factor = next(f for f in item.tradeoffs if f.value == "fuel_type_mismatch")
    assert factor.component == "use_case_fit"
    assert factor.metric == "constraint"
    assert factor.contribution == 0
    assert factor.message == messages_it.soft_tradeoff_message("fuel_type_mismatch")
    assert factor.message.startswith("Compromesso accettato:")
    assert "Trade-off" not in factor.message


def test_factor_messages_have_their_accents():
    texts = [
        *messages_it.POSITIVE_FACTOR_MESSAGES.values(),
        *messages_it.TRADEOFF_FACTOR_MESSAGES.values(),
    ]
    joined = " ".join(texts)
    for unaccented in (" e contenuto", " e elevato", "versatilita", " piu "):
        assert unaccented not in joined
