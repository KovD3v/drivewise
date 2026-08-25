from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import psycopg
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.rows import dict_row

from app.api.dependencies import (
    get_advisor_repository,
    get_guided_decisions_repository,
)
from app.api.routers.guided_decisions import get_guided_decision_clock
from app.main import app
from app.db.migrations import MIGRATIONS_PATH
from app.repositories.guided_decisions import (
    GuidedDecisionNotFoundError,
    GuidedDecisionsRepository,
    GuidedDecisionVersionConflictError,
)
from app.schemas.guided_decisions import (
    DecisionFact,
    DecisionProfile,
    GarageProfile,
    GuidedDecisionRecord,
)
from app.services.guided_decisions.engine import process_guided_decision_turn
from app.services.guided_decisions.interpreter import extract_profile_updates
from app.services.guided_decisions.questions import next_question
from app.services.guided_decisions.garage import (
    VehicleDimensions,
    evaluate_garage_compatibility,
)
from test_advisor_scoring import candidate as scoring_candidate


AS_OF = datetime(2026, 8, 12, 10, tzinfo=timezone.utc)
DECISION_ID = UUID("60000000-0000-4000-8000-000000000001")
VEHICLE_ID = UUID("00000000-0000-4000-8000-000000000001")
SPEC_ID = UUID("20000000-0000-4000-8000-000000000001")


class EmptyAdvisorRepository:
    def __init__(self) -> None:
        self.calls = []

    def list_candidates(self, *, as_of):
        self.calls.append(("list", as_of))
        return []

    def count_excluded_candidates(self, *, as_of):
        self.calls.append(("excluded", as_of))
        return {}


class CandidateAdvisorRepository(EmptyAdvisorRepository):
    def list_candidates(self, *, as_of):
        self.calls.append(("list", as_of))
        return [scoring_candidate(1)]


def test_sample_message_builds_structured_profile_and_next_question():
    repository = EmptyAdvisorRepository()

    result = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=1,
        current_profile=DecisionProfile(),
        message="Cerco un SUV per la famiglia e vorrei spendere circa 35.000 €",
        advisor_repository=repository,
        as_of=AS_OF,
    )

    profile = result.profile
    assert profile.vehicle_type.value == "car"
    assert profile.vehicle_type.source == "inferred"
    assert profile.vehicle_type.confirmed is False
    assert profile.category.value == "suv"
    assert profile.category.source == "user"
    assert profile.category.confirmed is True
    assert profile.budget_eur.value == 35_000
    assert profile.primary_use.value == "family"
    assert profile.family.value is True
    assert result.response.next_question.id == "annual_km"
    assert result.response.preview_ranking.status == "insufficient_inventory"
    assert result.response.preview_ranking.scoring_version == "advisor-v3.0"
    assert result.response.profile_completion > 0
    assert result.response.decision_confidence > 0
    assert repository.calls == [("list", AS_OF), ("excluded", AS_OF)]


def test_guided_profile_collects_family_and_constraints():
    repository = EmptyAdvisorRepository()
    result = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=1,
        current_profile=DecisionProfile(),
        message=(
            "Siamo in cinque con tre figli, città e autostrada, "
            "automatico obbligatorio"
        ),
        advisor_repository=repository,
        as_of=AS_OF,
    )

    profile = result.profile
    assert profile.children_count.value == 3
    assert profile.passengers_usual.value == 5
    assert profile.automatic_required.value is True
    assert profile.usage.value == ["city", "highway"]
    assert result.response.preview_ranking.status == "blocked"


def test_guided_provisional_preview_has_non_empty_items_and_confidence():
    repository = CandidateAdvisorRepository()
    result = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=1,
        current_profile=DecisionProfile(),
        message="Cerco un'auto in città con budget 20.000 euro",
        advisor_repository=repository,
        as_of=AS_OF,
    )

    assert result.response.preview_ranking.status == "provisional"
    assert any(
        group.items for group in result.response.preview_ranking.groups
    )
    assert 0 < result.response.decision_confidence <= 1


def test_guided_api_create_and_turn_keep_non_empty_provisional_preview():
    decisions_repository = InMemoryGuidedDecisionsRepository()
    advisor_repository = CandidateAdvisorRepository()
    app.dependency_overrides[get_guided_decisions_repository] = lambda: (
        decisions_repository
    )
    app.dependency_overrides[get_advisor_repository] = lambda: advisor_repository
    app.dependency_overrides[get_guided_decision_clock] = lambda: AS_OF
    try:
        client = TestClient(app)
        created = client.post(
            "/guided-decisions",
            json={"message": "Città, budget 20.000 euro"},
        )
        assert created.status_code == 200
        assert created.json()["previewRanking"]["status"] == "provisional"
        assert any(
            group["items"] for group in created.json()["previewRanking"]["groups"]
        )

        decision_id = created.json()["decisionId"]
        updated = client.post(
            f"/guided-decisions/{decision_id}/turns",
            json={"message": "15.000 km all'anno", "expectedProfileVersion": 1},
        )
        assert updated.status_code == 200
        assert updated.json()["previewRanking"]["status"] == "provisional"
        assert any(
            group["items"] for group in updated.json()["previewRanking"]["groups"]
        )
    finally:
        app.dependency_overrides.clear()


def test_interpreter_handles_negated_automatic_and_children_without_family():
    profile, updated = extract_profile_updates(
        "Non è obbligatorio l'automatico e non ho figli, preferisco la città",
        DecisionProfile(),
        expected_question_id=None,
        captured_at=AS_OF,
    )

    assert profile.automatic_required.value is False
    assert profile.constraint_modes.transmission == "soft"
    assert profile.children_count.value == 0
    assert profile.family.value is False
    assert profile.primary_use.value == "city"
    assert set(updated) >= {
        "automatic_required",
        "children_count",
        "family",
        "primary_use",
    }


def test_interpreter_unknown_phrase_does_not_change_profile():
    profile, updated = extract_profile_updates(
        "Forse vedremo più avanti",
        DecisionProfile(),
        expected_question_id=None,
        captured_at=AS_OF,
    )

    assert profile == DecisionProfile()
    assert updated == []


def test_contextual_constraint_modes_answer_uses_question_options():
    profile = _complete_guided_profile()
    assert next_question_for_test(profile) == "constraint_modes"

    result = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=4,
        current_profile=profile,
        message="budget, categoria e cambio",
        advisor_repository=EmptyAdvisorRepository(),
        as_of=AS_OF,
    )

    assert result.profile.constraint_modes.budget == "hard"
    assert result.profile.constraint_modes.body_style == "hard"
    assert result.profile.constraint_modes.transmission == "hard"
    assert result.response.next_question is None


def test_short_answer_uses_previous_next_question_context():
    repository = EmptyAdvisorRepository()
    first = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=1,
        current_profile=DecisionProfile(),
        message="SUV per la famiglia, budget 35.000 euro",
        advisor_repository=repository,
        as_of=AS_OF,
    )

    second = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=2,
        current_profile=first.profile,
        message="15.000",
        advisor_repository=repository,
        as_of=AS_OF,
    )

    assert second.profile.annual_km.value == 15_000
    assert second.response.updated_fields == ["annual_km"]
    assert second.response.next_question.id == "condition"


def test_garage_context_normalizes_decimal_metres_to_millimetres():
    profile = DecisionProfile(
        budget_eur=_fact(35_000),
        primary_use=_fact("family"),
        annual_km=_fact(15_000),
        condition=_fact("new"),
        category=_fact("suv"),
        preferred_fuel_type=_fact("petrol"),
        parking=_fact("garage"),
        priorities=_fact(["space"]),
    )
    repository = EmptyAdvisorRepository()

    result = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=2,
        current_profile=profile,
        message="2,5 m",
        advisor_repository=repository,
        as_of=AS_OF,
    )

    assert result.response.updated_fields == ["garage.door_width_mm"]
    assert result.profile.garage.door_width_mm.value == 2_500


def test_contextual_multi_select_answer_updates_priorities():
    profile = DecisionProfile(
        budget_eur=_fact(35_000),
        primary_use=_fact("family"),
        annual_km=_fact(15_000),
        condition=_fact("new"),
        category=_fact("suv"),
        preferred_fuel_type=_fact("petrol"),
        parking=_fact("outdoor_space"),
    )
    repository = EmptyAdvisorRepository()

    result = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=2,
        current_profile=profile,
        message="spazio e consumi",
        advisor_repository=repository,
        as_of=AS_OF,
    )

    assert result.response.updated_fields == ["priorities"]
    assert result.profile.priorities.value == ["running_cost", "space"]
    assert result.response.next_question is None


def test_garage_dimensions_become_missing_only_for_a_garage():
    repository = EmptyAdvisorRepository()
    result = process_guided_decision_turn(
        decision_id=DECISION_ID,
        profile_version=1,
        current_profile=DecisionProfile(),
        message=(
            "Cerco un SUV nuovo per la famiglia, budget 35.000 euro, "
            "15.000 km all'anno e ho un garage"
        ),
        advisor_repository=repository,
        as_of=AS_OF,
    )

    missing_keys = [item.key for item in result.response.missing_information]
    assert result.profile.parking.value == "garage"
    assert "garage.door_width_mm" in missing_keys
    assert "garage.useful_length_mm" in missing_keys
    assert result.response.next_question.id == "garage.door_width_mm"


def test_garage_compatibility_reports_tight_and_incompatible_geometry():
    profile = _complete_garage_profile(
        useful_length_mm=4_900,
        useful_width_mm=2_300,
        useful_height_mm=2_100,
        door_width_mm=2_050,
        door_height_mm=2_000,
    )

    tight = evaluate_garage_compatibility(
        profile,
        vehicle_id=VEHICLE_ID,
        spec_id=SPEC_ID,
        vehicle_dimensions=VehicleDimensions(4_400, 1_850, 1_700, 1_950),
    )
    incompatible = evaluate_garage_compatibility(
        profile,
        vehicle_id=VEHICLE_ID,
        spec_id=SPEC_ID,
        vehicle_dimensions=VehicleDimensions(4_400, 1_850, 1_700, 2_100),
    )

    assert tight.status == "tight"
    assert tight.margins.width_mm == 450
    assert incompatible.status == "incompatible"
    assert incompatible.margins.door_width_mm == -50


class InMemoryGuidedDecisionsRepository:
    def __init__(self) -> None:
        self.record = None

    def create(self, *, response, locale, market, user_message):
        self.record = GuidedDecisionRecord(
            id=response.decision_id,
            locale=locale,
            market=market,
            status=response.status,
            profile_version=response.profile_version,
            decision_profile=response.decision_profile,
            last_response=response.model_dump(mode="json", by_alias=True),
            created_at=AS_OF,
            updated_at=AS_OF,
        )

    def get(self, decision_id, *, for_update=False):
        if self.record is None or self.record.id != decision_id:
            raise GuidedDecisionNotFoundError(str(decision_id))
        return self.record

    def get_at_version(self, decision_id, *, expected_profile_version):
        record = self.get(decision_id, for_update=True)
        if record.profile_version != expected_profile_version:
            raise GuidedDecisionVersionConflictError(record.profile_version)
        return record

    def update(self, *, response, previous_profile_version, user_message):
        if self.record.profile_version != previous_profile_version:
            raise GuidedDecisionVersionConflictError(self.record.profile_version)
        self.record = self.record.model_copy(
            update={
                "profile_version": response.profile_version,
                "decision_profile": response.decision_profile,
                "last_response": response.model_dump(mode="json", by_alias=True),
                "updated_at": AS_OF,
            }
        )


@pytest.fixture
def guided_client():
    decisions_repository = InMemoryGuidedDecisionsRepository()
    advisor_repository = EmptyAdvisorRepository()
    app.dependency_overrides[get_guided_decisions_repository] = lambda: (
        decisions_repository
    )
    app.dependency_overrides[get_advisor_repository] = lambda: advisor_repository
    app.dependency_overrides[get_guided_decision_clock] = lambda: AS_OF
    yield TestClient(app), decisions_repository
    app.dependency_overrides.clear()


def test_guided_decision_api_uses_camel_case_contract_and_versioning(guided_client):
    client, _repository = guided_client
    created = client.post(
        "/guided-decisions",
        json={
            "message": "Cerco un SUV per la famiglia, budget 35.000 euro",
            "locale": "it-IT",
            "market": "IT",
        },
    )

    assert created.status_code == 200
    payload = created.json()
    assert payload["contractVersion"] == "guided-decision-v1"
    assert payload["profileVersion"] == 1
    assert "decisionProfile" in payload
    assert "profileCompletion" in payload
    assert "decision_profile" not in payload
    assert payload["decisionProfile"]["budgetEur"] == {
        "value": 35000.0,
        "confidence": 0.98,
        "source": "user",
        "confirmed": True,
        "updatedAt": "2026-08-12T10:00:00Z",
    }
    decision_id = payload["decisionId"]

    updated = client.post(
        f"/guided-decisions/{decision_id}/turns",
        json={"message": "15.000", "expectedProfileVersion": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["profileVersion"] == 2
    assert updated.json()["decisionProfile"]["annualKm"]["value"] == 15_000

    conflict = client.post(
        f"/guided-decisions/{decision_id}/turns",
        json={"message": "12.000", "expectedProfileVersion": 1},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == {
        "code": "profile_version_conflict",
        "currentProfileVersion": 2,
    }

    fetched = client.get(f"/guided-decisions/{decision_id}")
    assert fetched.status_code == 200
    assert fetched.json()["profileVersion"] == 2


def test_guided_decision_rejects_unsupported_market(guided_client):
    client, _repository = guided_client
    response = client.post(
        "/guided-decisions",
        json={"message": "Cerco un'auto", "market": "US"},
    )
    assert response.status_code == 422


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not configured",
)
def test_guided_decision_repository_persists_and_updates_profile_versions():
    database_url = os.environ["TEST_DATABASE_URL"]
    schema_name = f"guided_decision_{uuid4().hex}"

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
        try:
            conn.execute(
                sql.SQL("SET search_path TO {}, public").format(
                    sql.Identifier(schema_name)
                )
            )
            conn.execute(
                (MIGRATIONS_PATH / "0006_guided_decisions.sql").read_text()
            )
            conn.commit()
            repository = GuidedDecisionsRepository(conn)
            advisor_repository = EmptyAdvisorRepository()
            first = process_guided_decision_turn(
                decision_id=DECISION_ID,
                profile_version=1,
                current_profile=DecisionProfile(),
                message="SUV per la famiglia, budget 35.000 euro",
                advisor_repository=advisor_repository,
                as_of=AS_OF,
            )
            repository.create(
                response=first.response,
                locale="it-IT",
                market="IT",
                user_message="SUV per la famiglia, budget 35.000 euro",
            )
            conn.commit()

            persisted = repository.get_at_version(
                DECISION_ID,
                expected_profile_version=1,
            )
            second = process_guided_decision_turn(
                decision_id=DECISION_ID,
                profile_version=2,
                current_profile=persisted.decision_profile,
                message="15.000",
                advisor_repository=advisor_repository,
                as_of=AS_OF,
            )
            repository.update(
                response=second.response,
                previous_profile_version=1,
                user_message="15.000",
            )
            conn.commit()

            updated = repository.get(DECISION_ID)
            turn_versions = [
                row["profile_version"]
                for row in conn.execute(
                    """
                    SELECT profile_version
                    FROM guided_decision_turns
                    WHERE decision_id = %s
                    ORDER BY profile_version
                    """,
                    (DECISION_ID,),
                ).fetchall()
            ]
            assert updated.profile_version == 2
            assert updated.decision_profile.annual_km.value == 15_000
            assert turn_versions == [1, 2]
        finally:
            conn.rollback()
            conn.execute("SET search_path TO public")
            conn.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema_name)
                )
            )
            conn.commit()


def _complete_garage_profile(
    *,
    useful_length_mm: int,
    useful_width_mm: int,
    useful_height_mm: int,
    door_width_mm: int,
    door_height_mm: int,
) -> DecisionProfile:
    def fact(value):
        return DecisionFact(
            value=value,
            confidence=1,
            source="user",
            confirmed=True,
            updated_at=AS_OF,
        )

    return DecisionProfile(
        parking=fact("garage"),
        garage=GarageProfile(
            useful_length_mm=fact(useful_length_mm),
            useful_width_mm=fact(useful_width_mm),
            useful_height_mm=fact(useful_height_mm),
            door_width_mm=fact(door_width_mm),
            door_height_mm=fact(door_height_mm),
        ),
    )


def _fact(value):
    return DecisionFact(
        value=value,
        confidence=1,
        source="user",
        confirmed=True,
        updated_at=AS_OF,
    )


def _complete_guided_profile() -> DecisionProfile:
    return DecisionProfile(
        vehicle_type=_fact("car"),
        category=_fact("suv"),
        budget_eur=_fact(35_000),
        family=_fact(True),
        primary_use=_fact("family"),
        usage=_fact(["family"]),
        children_count=_fact(2),
        passengers_usual=_fact(4),
        annual_km=_fact(15_000),
        condition=_fact("any"),
        preferred_fuel_type=_fact("petrol"),
        priorities=_fact(["space"]),
        automatic_required=_fact(True),
        parking=_fact("outdoor_space"),
    )


def next_question_for_test(profile: DecisionProfile) -> str | None:
    question = next_question(profile)
    return question.id if question else None
