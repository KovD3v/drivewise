from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest
import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.api.dependencies import get_advisor_repository
from app.api.routers.advisor import get_advisor_clock
from app.main import app
from app.db.migrations import apply_migrations
from app.repositories.advisor import AdvisorRepository
from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.scoring import (
    SCORING_VERSION,
    build_assumptions,
    score_recommendations,
)


AS_OF = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
RUN_ID = UUID("50000000-0000-4000-8000-000000000001")
VEHICLE_ID = UUID("00000000-0000-4000-8000-000000000001")
SPEC_ID = UUID("20000000-0000-4000-8000-000000000001")
SOURCE_ID = UUID("10000000-0000-4000-8000-000000000001")


def exact_pair(
    *,
    condition: str,
    listing_suffix: int,
    mileage: int | None,
) -> dict[str, Any]:
    offer_id = UUID(f"30000000-0000-4000-8000-{listing_suffix:012d}")
    return {
        "vehicle": {
            "id": VEHICLE_ID,
            "canonical_key": "it-fiat-panda-2026",
            "model_family_key": "it-fiat-panda",
            "make": "Fiat",
            "model": "Panda",
            "model_year": 2026,
            "body_style": "city_car",
            "fuel_type": "mild_hybrid_petrol",
            "market": "IT",
            "base_price_eur": 18_000,
        },
        "spec": {
            "id": SPEC_ID,
            "variant_key": "it-fiat-panda-2026-city",
            "is_default": True,
            "trim": "City",
            "body_style": "city_car",
            "fuel_type": "mild_hybrid_petrol",
            "list_price_eur": 18_000,
            "drivetrain": "fwd",
            "transmission": "manual",
            "engine": "1.0 mild hybrid",
            "horsepower": 70,
            "battery_kwh": None,
            "energy_consumption_kwh_100km": None,
            "consumption_l_100km": 5.0,
            "wltp_range_km": None,
            "co2_g_km": 110,
            "euro_emission_standard": "Euro 6e",
            "seats": 4,
            "cargo_volume_liters": 225,
        },
        "offer": {
            "id": offer_id,
            "vehicle_id": VEHICLE_ID,
            "spec_id": SPEC_ID,
            "source_id": SOURCE_ID,
            "listing_ref": f"panda-{condition}-{listing_suffix}",
            "title": f"Fiat Panda {condition}",
            "price_eur": 17_500,
            "mileage": mileage,
            "condition": condition,
            "location_region": "Piemonte",
            "source_url": f"https://example.test/offers/{listing_suffix}",
            "listed_at": "2026-07-10",
            "last_seen_at": "2026-07-15T10:00:00Z",
            "valid_until": "2026-08-15T00:00:00Z",
            "is_active": True,
        },
        "reviewed": True,
        "source": {
            "name": "Reviewed catalog",
            "license": "Synthetic test data",
            "ranking_permission": "permitted",
        },
        "provenance": [
            {
                "metric": metric,
                "source_name": "Reviewed catalog",
                "source_url": "https://example.test/specs/panda",
                "observed_at": "2026-07-14T00:00:00Z",
            }
            for metric in (
                "body_style",
                "fuel_type",
                "seats",
                "cargo_volume_liters",
                "consumption_l_100km",
            )
        ],
    }


class FakeAdvisorRepository:
    def __init__(self) -> None:
        self.as_of_calls: list[datetime] = []
        self.run_payload = None
        self.run_metadata = None
        self.saved_groups = None
        self.completed_run_id = None

    def list_candidates(self, *, as_of):
        self.as_of_calls.append(as_of)
        return [
            exact_pair(condition="new", listing_suffix=1, mileage=None),
            exact_pair(condition="certified", listing_suffix=2, mileage=8_000),
        ]

    def count_excluded_candidates(self, *, as_of):
        self.as_of_calls.append(as_of)
        return {"stale_offer": 2}

    def create_run(self, request_payload, **metadata):
        self.run_payload = request_payload
        self.run_metadata = metadata
        return RUN_ID

    def save_items(self, run_id, groups):
        self.saved_groups = (run_id, groups)

    def mark_run_completed(self, run_id):
        self.completed_run_id = run_id


@pytest.fixture
def fake_repository():
    repository = FakeAdvisorRepository()
    app.dependency_overrides[get_advisor_repository] = lambda: repository
    app.dependency_overrides[get_advisor_clock] = lambda: AS_OF
    yield repository
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_repository):
    return TestClient(app)


def test_post_advisor_v2_returns_frontend_shape_and_persists_run_context(
    client,
    fake_repository,
):
    response = client.post(
        "/advisor/recommendations",
        json={
            "budget_max_eur": 20_000,
            "primary_use": "city",
            "condition": "any",
            "priorities": ["price", "efficiency_range"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == str(RUN_ID)
    assert payload["scoring_version"] == SCORING_VERSION
    expected_assumptions = build_assumptions(
        AdvisorRecommendationRequest(
            budget_max_eur=20_000,
            primary_use="city",
            condition="any",
            priorities=["price", "efficiency_range"],
        )
    )
    assert payload["assumptions"] == expected_assumptions
    assert payload["excluded_counts_by_reason"] == {"stale_offer": 2}
    assert [group["condition"] for group in payload["groups"]] == ["new", "used"]
    assert payload["groups"][0]["items"][0]["offer"]["condition"] == "new"
    assert (
        payload["groups"][1]["items"][0]["offer"]["condition"] == "certified"
    )
    first_item = payload["groups"][0]["items"][0]
    assert first_item["selected_spec"]["id"] == str(SPEC_ID)
    assert not {
        "identity",
        "dimensions",
        "powertrain",
        "transmission_details",
        "performance",
        "official_efficiency",
        "maintenance_schedule",
        "safety",
        "technology_comfort",
        "media",
    }.intersection(first_item["selected_spec"])
    assert set(first_item["component_scores"]) == {
        "price_fit",
        "use_case_fit",
        "running_cost",
        "space",
        "efficiency_range",
    }
    assert "document_evidence" not in first_item
    assert "best_listing" not in first_item
    assert "rationale" not in first_item

    assert fake_repository.as_of_calls == [AS_OF, AS_OF]
    assert fake_repository.run_payload["annual_km"] == 10_000
    assert fake_repository.run_payload["scoring_version"] == SCORING_VERSION
    assert fake_repository.run_payload["evaluated_at"] == AS_OF.isoformat()
    assert fake_repository.run_payload["annual_km_defaulted"] is True
    assert fake_repository.run_metadata == {
        "scoring_version": SCORING_VERSION,
        "assumptions": expected_assumptions,
        "exclusion_counts": {"stale_offer": 2},
    }
    assert fake_repository.saved_groups[0] == RUN_ID
    assert [group.condition for group in fake_repository.saved_groups[1]] == [
        "new",
        "used",
    ]
    assert fake_repository.completed_run_id == RUN_ID


def test_post_advisor_accepts_v3_priorities_and_rejects_unknown(client):
    response = client.post(
        "/advisor/recommendations",
        json={
            "budget_max_eur": 20_000,
            "primary_use": "city",
            "priorities": ["safety"],
        },
    )
    assert response.status_code == 200
    invalid = client.post(
        "/advisor/recommendations",
        json={
            "budget_max_eur": 20_000,
            "primary_use": "city",
            "priorities": ["not_a_priority"],
        },
    )
    assert invalid.status_code == 422


def test_post_advisor_persists_v3_breakdown_and_active_versions(
    client,
    fake_repository,
):
    response = client.post(
        "/advisor/recommendations",
        json={
            "budget_max_eur": 20_000,
            "primary_use": "city",
            "priorities": ["safety"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scoring_version"] == "advisor-v3.0"
    item = payload["groups"][0]["items"][0]
    assert item["structural_fit"] is not None
    assert item["decision_confidence"] is not None
    assert item["module_versions"]
    assert item["evidence"]["legacy_compatibility"]["label"] == (
        "v2_normalized_weights"
    )
    assert fake_repository.run_payload["active_versions"]["scoring"] == "advisor-v3.0"
    stored_item = fake_repository.saved_groups[1][0].items[0]
    assert stored_item.score_composition


def test_post_advisor_does_not_complete_run_when_item_write_fails(
    fake_repository,
):
    def fail_save(*_args):
        raise RuntimeError("item write failed")

    fake_repository.save_items = fail_save
    with pytest.raises(RuntimeError, match="item write failed"):
        TestClient(app).post(
            "/advisor/recommendations",
            json={"budget_max_eur": 20_000, "primary_use": "city"},
        )
    assert fake_repository.completed_run_id is None


class RecordingResult:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []

    def fetchall(self):
        return self.rows


class RecordingConnection:
    def __init__(self, rows=None) -> None:
        self.calls: list[tuple[str, tuple[Any, ...] | None]] = []
        self.rows = rows or []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return RecordingResult(self.rows)


def test_model_analysis_repository_uses_broad_exact_spec_query():
    conn = RecordingConnection()
    repository = AdvisorRepository(conn)

    assert repository.list_model_analysis_candidates() == []
    sql, params = conn.calls[0]
    assert params is None
    assert "LEFT JOIN vehicle_specs" in sql
    assert "l.spec_id = s.id" in sql
    assert "l.last_seen_at >=" not in sql
    assert "import_run.status = 'completed'" not in sql


def test_candidate_maps_source_aware_decision_context():
    row = {
        "vehicle_id": VEHICLE_ID,
        "canonical_key": "it-fiat-panda-2026",
        "model_family_key": "it-fiat-panda",
        "make": "Fiat",
        "model": "Panda",
        "model_year": 2026,
        "vehicle_body_style": "city_car",
        "vehicle_fuel_type": "mild_hybrid_petrol",
        "market": "IT",
        "base_price_eur": 18_000,
        "spec_id": SPEC_ID,
        "variant_key": "it-fiat-panda-2026-city",
        "is_default": True,
        "trim": "City",
        "spec_body_style": "city_car",
        "spec_fuel_type": "mild_hybrid_petrol",
        "list_price_eur": 18_000,
        "drivetrain": "fwd",
        "transmission": "manual",
        "engine": "1.0 mild hybrid",
        "horsepower": 70,
        "battery_kwh": None,
        "energy_consumption_kwh_100km": None,
        "consumption_l_100km": 5.0,
        "wltp_range_km": None,
        "co2_g_km": 110,
        "euro_emission_standard": "Euro 6e",
        "seats": 4,
        "cargo_volume_liters": 225,
        "generation_name": "Fourth generation",
        "restyling_label": "2024 update",
        "category": "city_car",
        "length_mm": 4189,
        "width_mm": 1859,
        "height_mm": 1551,
        "curb_weight_kg": 1055,
        "engine_code": "GSE-T3",
        "power_kw": 96.0,
        "transmission_type": "manual",
        "acceleration_0_100_s": 10.5,
        "top_speed_kmh": 180,
        "braking_100_0_m": 38.0,
        "maintenance_items": [],
        "safety_ratings": [
            {
                "overall_stars": 5,
                "source_url": "https://example.test/safety/panda",
            }
        ],
        "safety_features": [
            {
                "category": "adas",
                "name": "Autonomous emergency braking",
                "source_url": "https://example.test/adas/panda",
            }
        ],
        "technology_comfort_features": [],
        "listing_id": UUID("30000000-0000-4000-8000-000000000001"),
        "source_id": SOURCE_ID,
        "listing_ref": "panda-new-1",
        "title": "Fiat Panda new",
        "price_eur": 17_500,
        "mileage": None,
        "condition": "new",
        "location_region": "Piemonte",
        "source_url": "https://example.test/offers/1",
        "listed_at": "2026-07-10",
        "last_seen_at": "2026-07-15T10:00:00Z",
        "valid_until": "2026-08-15T00:00:00Z",
        "is_active": True,
        "listing_source_name": "Reviewed catalog",
        "listing_source_license": "Synthetic test data",
        "listing_source_ranking_permission": "permitted",
        "import_status": "completed",
        "spec_provenance": [],
    }
    candidate = AdvisorRepository(RecordingConnection([row])).list_candidates(
        as_of=AS_OF
    )[0]
    context = candidate["decision_context"]
    assert context["dimensions"]["length_mm"] == 4189
    assert context["powertrain"]["power_kw"] == 96.0
    assert context["safety"]["ratings"][0]["overall_stars"] == 5
    assert context["safety"]["ratings"][0]["source_url"].startswith("https://")
    assert context["safety"]["features"][0]["category"] == "adas"

    row.update(
        maintenance_items=None,
        safety_ratings=None,
        safety_features=None,
        technology_comfort_features=None,
        spec_provenance=None,
    )
    empty_candidate = AdvisorRepository(RecordingConnection([row])).list_candidates(
        as_of=AS_OF
    )[0]
    empty_context = empty_candidate["decision_context"]
    assert empty_context["maintenance"] == []
    assert empty_context["safety"]["ratings"] == []
    assert empty_context["safety"]["features"] == []
    assert empty_context["technology_comfort"] == []


def test_candidate_query_keeps_source_aware_children_correlated_and_permitted():
    conn = RecordingConnection()
    AdvisorRepository(conn).list_candidates(as_of=AS_OF)
    sql = conn.calls[0][0]

    def aggregate_fragment(alias):
        end = sql.index(f") AS {alias}") + len(f") AS {alias}")
        start = sql.rfind("COALESCE(", 0, end)
        return sql[start:end]

    aggregates = (
        ("spec_provenance", "vehicle_spec_provenance", "provenance"),
        ("maintenance_items", "vehicle_maintenance_items", "item"),
        ("safety_ratings", "vehicle_safety_ratings", "rating"),
        ("safety_features", "vehicle_features", "feature"),
        (
            "technology_comfort_features",
            "vehicle_features",
            "feature",
        ),
    )
    for alias, child_table, child_alias in aggregates:
        fragment = aggregate_fragment(alias)
        assert child_table in fragment
        assert f"WHERE {child_alias}.spec_id = s.id" in fragment
        assert f"{child_alias}_source.ranking_permission = 'permitted'" in fragment
        assert "'[]'::jsonb" in fragment
        assert f") AS {alias}" in fragment
    assert "feature.category IN ('adas', 'safety')" in aggregate_fragment(
        "safety_features"
    )
    assert "feature.category IN ('technology', 'comfort')" in aggregate_fragment(
        "technology_comfort_features"
    )
    outer_query = sql[sql.index("FROM listings AS l") :]
    for child_table in (
        "vehicle_spec_provenance",
        "vehicle_maintenance_items",
        "vehicle_safety_ratings",
        "vehicle_features",
    ):
        assert f"JOIN {child_table}" not in outer_query


def test_candidate_query_recognizes_phev_without_removing_source_gates():
    conn = RecordingConnection()
    AdvisorRepository(conn).list_candidates(as_of=AS_OF)
    sql = conn.calls[0][0]
    assert "'plug_in_hybrid_petrol'" in sql
    assert "unsupported_phev" not in sql
    assert "ranking_permission = 'permitted'" in sql
    assert "import_run.status = 'completed'" in sql


def test_repository_persists_run_and_each_condition_item_with_v2_breakdown():
    scoring = score_recommendations(
        AdvisorRecommendationRequest(
            budget_max_eur=20_000,
            primary_use="city",
            condition="any",
        ),
        [
            exact_pair(condition="new", listing_suffix=1, mileage=None),
            exact_pair(condition="used", listing_suffix=2, mileage=8_000),
        ],
        as_of=AS_OF,
        initial_excluded_counts={"stale_offer": 2},
    )
    conn = RecordingConnection()
    repository = AdvisorRepository(conn)
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
        condition="any",
    )
    assumptions = build_assumptions(request)

    run_id = repository.create_run(
        {"budget_max_eur": 20_000},
        scoring_version=SCORING_VERSION,
        assumptions=assumptions,
        exclusion_counts=scoring.excluded_counts_by_reason,
    )
    repository.save_items(run_id, scoring.groups)

    run_sql, run_params = conn.calls[0]
    assert "scoring_version" in run_sql
    assert "assumptions" in run_sql
    assert "exclusion_counts" in run_sql
    assert run_params[2] == SCORING_VERSION
    assert isinstance(run_params[3], Jsonb)
    assert isinstance(run_params[4], Jsonb)

    item_calls = conn.calls[1:]
    assert len(item_calls) == 2
    assert all("listing_id" in sql and "spec_id" in sql for sql, _ in item_calls)
    assert all("condition_group" in sql and "score_breakdown" in sql for sql, _ in item_calls)
    assert [params[5] for _, params in item_calls] == ["new", "used"]
    assert [params[6] for _, params in item_calls] == [1, 1]
    assert [params[3] for _, params in item_calls] == [
        UUID("30000000-0000-4000-8000-000000000001"),
        UUID("30000000-0000-4000-8000-000000000002"),
    ]
    assert all(params[4] == SPEC_ID for _, params in item_calls)
    assert all(params[9] == SCORING_VERSION for _, params in item_calls)
    assert all(isinstance(params[10], Jsonb) for _, params in item_calls)


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not configured",
)
def test_repository_v2_persistence_round_trips_in_postgres():
    database_url = os.environ["TEST_DATABASE_URL"]
    apply_migrations(database_url)
    request = AdvisorRecommendationRequest(
        budget_max_eur=20_000,
        primary_use="city",
        condition="used",
        priorities=["price"],
    )
    assumptions = build_assumptions(request)
    scoring = score_recommendations(
        request,
        [exact_pair(condition="used", listing_suffix=1, mileage=8_000)],
        as_of=AS_OF,
        initial_excluded_counts={"stale_offer": 2},
    )

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        repository = AdvisorRepository(conn)
        run_id = repository.create_run(
            request.model_dump(mode="json"),
            scoring_version=SCORING_VERSION,
            assumptions=assumptions,
            exclusion_counts=scoring.excluded_counts_by_reason,
        )
        try:
            repository.save_items(run_id, scoring.groups)
            repository.mark_run_completed(run_id)
            row = conn.execute(
                """
                SELECT
                  run.request_payload,
                  run.scoring_version AS run_scoring_version,
                  run.assumptions,
                  run.exclusion_counts,
                  item.vehicle_id,
                  item.listing_id,
                  item.spec_id,
                  item.condition_group,
                  item.rank,
                  item.scoring_version AS item_scoring_version,
                  item.score_breakdown
                FROM recommendation_runs AS run
                JOIN recommendation_items AS item ON item.run_id = run.id
                WHERE run.id = %s
                """,
                (run_id,),
            ).fetchone()

            assert row["request_payload"]["budget_max_eur"] == 20_000
            assert row["run_scoring_version"] == SCORING_VERSION
            assert row["assumptions"] == assumptions
            assert row["exclusion_counts"] == {"stale_offer": 2}
            assert row["vehicle_id"] == VEHICLE_ID
            assert row["listing_id"] == UUID(
                "30000000-0000-4000-8000-000000000001"
            )
            assert row["spec_id"] == SPEC_ID
            assert row["condition_group"] == "used"
            assert row["rank"] == 1
            assert row["item_scoring_version"] == SCORING_VERSION
            assert set(row["score_breakdown"]["component_scores"]) == {
                "price_fit",
                "use_case_fit",
                "running_cost",
                "space",
                "efficiency_range",
            }
        finally:
            conn.execute("DELETE FROM recommendation_runs WHERE id = %s", (run_id,))
