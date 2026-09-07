from datetime import datetime, timezone

import pytest

from app.schemas.guided_decisions import DecisionProfile
from app.services.guided_decisions.engine import process_guided_decision_turn
from app.services.guided_decisions.interpreter import extract_profile_updates
from app.services.guided_decisions.questions import QUESTION_DEFINITIONS, next_question
from test_guided_decisions import (
    DECISION_ID,
    EmptyAdvisorRepository,
    _complete_guided_profile,
    _fact,
    guided_client as guided_client,
)

AS_OF = datetime(2026, 9, 7, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "key,answer,value",
    [
        ("budget_eur", "25000", 25000),
        ("annual_km", "12000", 12000),
        ("children_count", "2", 2),
        ("children_count", "due", 2),
        ("children_count", "zero", 0),
        ("passengers_usual", "2", 2),
        ("passengers_usual", "due", 2),
        ("automatic_required", "sì", True),
        ("automatic_required", "no", False),
        ("parking", "sì", "garage"),
        ("parking", "no", "none"),
        ("primary_use", "città", "city"),
        ("condition", "entrambe", "any"),
        ("category", "utilitaria", "city_car"),
        ("preferred_fuel_type", "benzina", "petrol"),
        ("priorities", "spazio e consumi", ["running_cost", "space"]),
        ("usage", "famiglia", ["family"]),
        ("usage", "famiglia e autostrada", ["family", "highway"]),
        *[
            (q.key, "2500", 2500)
            for q in QUESTION_DEFINITIONS
            if q.key.startswith("garage.")
        ],
        *[
            (q.key, option, [option] if q.question.type == "multi_select" else option)
            for q in QUESTION_DEFINITIONS
            if q.key != "constraint_modes" and q.question.constraints
            for option in q.question.constraints.options
        ],
    ],
)
def test_short_answer_advances_active_question(key, answer, value):
    profile = _complete_guided_profile()
    profile.parking = _fact("garage")
    for name in type(profile.garage).model_fields:
        setattr(profile.garage, name, _fact(5000))
    target = profile.garage if key.startswith("garage.") else profile
    setattr(target, key.split(".")[-1], None)
    assert next_question(profile).id == key

    result = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=2,
        current_profile=profile,
        message=answer,
        advisor_repository=EmptyAdvisorRepository(),
        as_of=AS_OF,
    )
    target = result.profile.garage if key.startswith("garage.") else result.profile
    assert getattr(target, key.split(".")[-1]).value == value
    assert key in result.response.updated_fields
    assert (
        result.response.next_question is None or result.response.next_question.id != key
    )
    DecisionProfile.model_validate_json(result.profile.model_dump_json())


@pytest.mark.parametrize(
    "answer",
    [
        "nessuno",
        "nessun vincolo obbligatorio",
        "nessun vincolo",
        "nessuna preferenza obbligatoria",
        "tutti morbidi",
        "none",
    ],
)
def test_no_hard_constraints_is_explicit_and_round_trips(answer):
    original = _complete_guided_profile()
    profile, updated = extract_profile_updates(
        answer,
        original,
        expected_question_id="constraint_modes",
        captured_at=AS_OF,
    )
    assert profile.constraint_modes_confirmed.value is True
    assert all(
        value == "soft" for value in profile.constraint_modes.model_dump().values()
    )
    assert "constraint_modes_confirmed" in updated
    assert profile.parking == original.parking
    restored = DecisionProfile.model_validate_json(profile.model_dump_json())
    assert next_question(restored) is None
    assert DecisionProfile().constraint_modes_confirmed is None


@pytest.mark.parametrize(
    "raw,value",
    [
        ("12,5k", 12500),
        ("12.5k", 12500),
        ("2,5k", 2500),
        ("12k", 12000),
        ("12 mila", 12000),
        ("12,5 mila", 12500),
        ("12.500", 12500),
        ("12,500", 12500),
        ("12 500", 12500),
    ],
)
@pytest.mark.parametrize(
    "key,template",
    [
        ("budget_eur", "{}"),
        ("annual_km", "{}"),
        ("budget_eur", "budget {} euro"),
        ("annual_km", "{} km annui"),
    ],
)
def test_quantities_preserve_decimal_multiplier(key, template, raw, value):
    profile, _ = extract_profile_updates(
        template.format(raw),
        DecisionProfile(),
        expected_question_id=key,
        captured_at=AS_OF,
    )
    assert getattr(profile, key).value == value


def test_no_hard_constraints_survives_api_get_and_new_session(guided_client):
    client, repository = guided_client
    created = client.post(
        "/guided-decisions", json={"message": "SUV per la famiglia, budget 35000 euro"}
    ).json()
    repository.record = repository.record.model_copy(
        update={"decision_profile": _complete_guided_profile()}
    )
    response = client.post(
        f"/guided-decisions/{created['decisionId']}/turns",
        json={"message": "nessuno", "expectedProfileVersion": 1},
    )
    assert response.status_code == 200
    assert response.json()["nextQuestion"] is None
    fetched = client.get(f"/guided-decisions/{created['decisionId']}").json()
    assert fetched["decisionProfile"]["constraintModesConfirmed"]["value"] is True
    fresh = client.post(
        "/guided-decisions", json={"message": "SUV per la famiglia, budget 35000 euro"}
    ).json()
    assert fresh["decisionProfile"]["constraintModesConfirmed"] is None


@pytest.mark.parametrize(
    "answer", ["budget", "body_style", "fuel_type", "transmission", "garage"]
)
def test_each_hard_constraint_option_completes_question(answer):
    profile, _ = extract_profile_updates(
        answer,
        _complete_guided_profile(),
        expected_question_id="constraint_modes",
        captured_at=AS_OF,
    )
    assert getattr(profile.constraint_modes, answer) == "hard"
    assert profile.constraint_modes_confirmed.value is True
    assert next_question(profile) is None


def test_no_constraints_can_clear_previous_hard_modes():
    profile = _complete_guided_profile()
    profile.constraint_modes.budget = "hard"
    profile.constraint_modes.transmission = "hard"
    updated, _ = extract_profile_updates(
        "nessuno",
        profile,
        expected_question_id="constraint_modes",
        captured_at=AS_OF,
    )
    assert all(
        mode == "soft" for mode in updated.constraint_modes.model_dump().values()
    )
    assert updated.constraint_modes_confirmed.value is True


@pytest.mark.parametrize(
    "key,answer",
    [
        ("annual_km", "0"),
        ("budget_eur", "0"),
        ("passengers_usual", "0"),
        ("children_count", "-1"),
        ("automatic_required", "forse"),
        ("constraint_modes", "non so"),
    ],
)
def test_invalid_short_answers_do_not_complete_question(key, answer):
    profile, fields = extract_profile_updates(
        answer,
        DecisionProfile(),
        expected_question_id=key,
        captured_at=AS_OF,
    )
    assert profile == DecisionProfile()
    assert fields == []
