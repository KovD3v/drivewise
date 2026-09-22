import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.rows import dict_row

from app.api.dependencies import get_vehicles_repository
from app.db.migrations import MIGRATIONS_PATH, run_migrations
from app.ingestion.catalog import CatalogValidationError
from app.ingestion.catalog_v2 import CatalogV2
from app.ingestion.catalog_v2_writer import (
    publish_catalog_v2,
    stage_catalog_v2,
    verify_artifacts,
)
from app.main import app
from app.repositories.advisor import AdvisorRepository
from app.repositories.filters import ListingFilters, VehicleFilters
from app.repositories.listings import ListingsRepository
from app.repositories.vehicles import VehiclesRepository
from app.schemas.advisor import AdvisorRecommendationRequest, ModelAnalysisRequest
from app.services.advisor.scoring import build_recommendations
from app.schemas.listings import ListingWithVehicle
from app.schemas.vehicles import VehicleDetail, VehicleResolveRequest, VehicleSpec
from app.services.advisor.model_analysis import build_model_analysis
from app.services.vehicles.resolver import resolve_vehicle_query

ROOT = Path(__file__).resolve().parents[3]


def bundle(tmp_path):
    data = json.loads(
        (ROOT / "data/fixtures/catalog/catalog-v2.synthetic.json").read_text()
    )
    for snapshot in data["snapshots"]:
        content = f"Synthetic test evidence {snapshot['id']}".encode()
        path = tmp_path / snapshot["artifact_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        snapshot["content_sha256"] = hashlib.sha256(content).hexdigest()
    return data


@pytest.fixture
def conn():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    run_migrations(url)
    with psycopg.connect(url, row_factory=dict_row, autocommit=True) as connection:
        with connection.transaction(force_rollback=True):
            schema = f"v2_publication_{uuid4().hex}"
            connection.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
            )
            connection.execute(
                sql.SQL("SET LOCAL search_path TO {}, public").format(
                    sql.Identifier(schema)
                )
            )
            for migration in sorted(MIGRATIONS_PATH.glob("*.sql")):
                if not migration.name.startswith("0001"):
                    connection.execute(migration.read_text())
            yield connection


def publish(conn, data, root, **kwargs):
    batch_id = stage_catalog_v2(
        conn, CatalogV2.model_validate(data), artifact_root=root
    )
    assert (
        publish_catalog_v2(conn, batch_id, artifact_root=root, **kwargs) == "published"
    )
    return batch_id


def test_artifact_hash_and_symlink_escape(tmp_path):
    data = bundle(tmp_path)
    payload = CatalogV2.model_validate(data)
    verify_artifacts(payload, tmp_path)
    path = tmp_path / data["snapshots"][0]["artifact_path"]
    path.write_text("tampered")
    with pytest.raises(CatalogValidationError, match="hash-mismatched"):
        verify_artifacts(payload, tmp_path)
    path.unlink()
    path.symlink_to("/etc/hosts")
    with pytest.raises(CatalogValidationError, match="unsafe"):
        verify_artifacts(payload, tmp_path)


def test_staging_publication_retry_and_api(conn, tmp_path):
    data = bundle(tmp_path)
    payload = CatalogV2.model_validate(data)
    batch = stage_catalog_v2(conn, payload, artifact_root=tmp_path)
    assert stage_catalog_v2(conn, payload, artifact_root=tmp_path) == batch
    assert (
        conn.execute("SELECT count(*) AS n FROM source_snapshots").fetchone()["n"] == 0
    )
    assert publish_catalog_v2(conn, batch, artifact_root=tmp_path) == "published"
    assert publish_catalog_v2(conn, batch, artifact_root=tmp_path) == "unchanged"
    repo = VehiclesRepository(conn)
    vehicles = repo.list_vehicles(VehicleFilters(make="Acme"))
    assert len(vehicles) == 3
    assert len({v["generation_key"] for v in vehicles}) == 2
    unknown = next(v for v in vehicles if v["model_year"] is None)
    detail = VehicleDetail.model_validate(repo.get_vehicle(unknown["id"]))
    assert detail.model_year is None and detail.catalog_version == 2
    response = resolve_vehicle_query(
        VehicleResolveRequest(query="Acme Metro City"),
        repo.list_resolve_candidates("IT"),
    )
    assert response.status == "ambiguous"
    assert all("model_year" not in m.matched_fields for m in response.matches)
    counts = conn.execute("SELECT count(*) AS n FROM fact_decisions").fetchone()["n"]
    assert counts == 3
    vehicle = next(v for v in vehicles if v["canonical_key"] == "metro-g2-2026")
    app.dependency_overrides[get_vehicles_repository] = lambda: repo
    try:
        with TestClient(app) as client:
            facts = client.get(f"/vehicles/{vehicle['id']}/facts")
            assert facts.status_code == 200
            assert facts.json()[0]["status"] == "conflicted"
            assert facts.json()[0]["value_min"] is None
            assert not facts.json()[0]["eligible"]
            assert client.get(f"/vehicles/{uuid4()}/facts").status_code == 404
            assert client.get(f"/vehicles/{unknown['id']}").status_code == 200
    finally:
        app.dependency_overrides.clear()
    # Same IDs can be re-imported in another complete bundle; old bytes are immutable.
    data["decisions"][2]["reason"] = "Changed immutable decision"
    batch = stage_catalog_v2(
        conn, CatalogV2.model_validate(data), artifact_root=tmp_path
    )
    with pytest.raises(CatalogValidationError, match="Immutable"):
        publish_catalog_v2(conn, batch, artifact_root=tmp_path)
    assert (
        conn.execute(
            "SELECT published_at FROM catalog_v2_batches WHERE id = %s", (batch,)
        ).fetchone()["published_at"]
        is None
    )
    assert (
        conn.execute("SELECT count(*) AS n FROM fact_decisions").fetchone()["n"]
        == counts
    )


def add_fact(data, metric, value, context=None, variant="metro-g1-ice"):
    observation = {
        "id": str(uuid4()),
        "snapshot_id": data["snapshots"][0]["id"],
        "variant_key": variant,
        "metric": metric,
        "raw_value": str(value),
        "raw_unit": "count",
        "value_min": value,
        "value_max": value,
        "unit": "count",
        "context": context or {"market": "IT"},
        "evidence_excerpt": "Synthetic test fact",
        "evidence_locator": "test",
        "extractor_version": "test-1",
    }
    units = {"cargo_volume_liters": "l", "liquid_consumption_l_100km": "l/100km"}
    observation["unit"] = observation["raw_unit"] = units.get(metric, "count")
    decision = {
        "id": str(uuid4()),
        "variant_key": variant,
        "metric": metric,
        "context": observation["context"],
        "status": "verified",
        "selected_observation_id": observation["id"],
        "evidence_ids": [observation["id"]],
        "reason": "Synthetic publication test",
        "actor_kind": "human",
        "actor_id": "test",
        "policy_version": "test-1",
        "decided_at": "2026-09-15T12:00:00Z",
    }
    data["observations"].append(observation)
    data["decisions"].append(decision)
    return decision


def test_revocation_conflicts_contexts_and_stale_replay(conn, tmp_path):
    data = bundle(tmp_path)
    # This is a simulated permitted source, not real vehicle data.
    data["sources"][0]["ranking_permission"] = "permitted"
    data["snapshots"][0]["evidence_kind"] = "sourced"
    first = add_fact(data, "seats", 5)
    publish(conn, data, tmp_path)

    def seats():
        return conn.execute(
            "SELECT seats FROM catalog_read_specs WHERE variant_key = 'metro-g1-ice'"
        ).fetchone()["seats"]

    assert seats() == 5
    conn.execute(
        "UPDATE sources SET ranking_permission = 'not_permitted' WHERE source_key = 'synthetic-v2'"
    )
    assert seats() is None
    revised = copy.deepcopy(data)
    revised["sources"][0]["notes"] = "Different batch, same permission claim"
    publish(conn, revised, tmp_path)
    assert seats() is None  # replay did not restore permission
    conn.execute(
        "UPDATE sources SET ranking_permission = 'permitted' WHERE source_key = 'synthetic-v2'"
    )
    assert seats() == 5
    conflict = copy.deepcopy(first)
    competing = copy.deepcopy(revised["observations"][-1])
    competing.update(id=str(uuid4()), value_min=4, value_max=4, raw_value="4")
    revised["observations"].append(competing)
    conflict.update(
        id=str(uuid4()),
        supersedes_id=first["id"],
        status="conflicted",
        selected_observation_id=None,
        evidence_ids=[first["selected_observation_id"], competing["id"]],
    )
    revised["decisions"].append(conflict)
    publish(conn, revised, tmp_path)
    assert seats() is None
    stale = copy.deepcopy(data)
    stale["sources"][0]["notes"] = "Old complete history"
    publish(conn, stale, tmp_path)
    assert seats() is None  # older bundles cannot regress the chain head
    # A competing successor rolls back, including any otherwise valid new facts.
    fork = copy.deepcopy(data)
    other = copy.deepcopy(first)
    other.update(id=str(uuid4()), supersedes_id=first["id"])
    fork["decisions"].append(other)
    add_fact(
        fork,
        "cargo_volume_liters",
        300,
        {"market": "IT", "method": "VDA", "seating_configuration": "all_seats_up"},
    )
    batch = stage_catalog_v2(
        conn, CatalogV2.model_validate(fork), artifact_root=tmp_path
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        publish_catalog_v2(conn, batch, artifact_root=tmp_path)
    assert (
        conn.execute(
            "SELECT count(*) AS n FROM spec_observations WHERE metric = 'cargo_volume_liters'"
        ).fetchone()["n"]
        == 0
    )


def test_intervals_and_multiple_contexts_are_not_flattened(conn, tmp_path):
    data = bundle(tmp_path)
    data["sources"][0]["ranking_permission"] = "permitted"
    data["snapshots"][0]["evidence_kind"] = "sourced"
    add_fact(data, "seats", 5)
    add_fact(data, "seats", 4, {"market": "IT", "configuration_key": "sport"})
    add_fact(
        data,
        "liquid_consumption_l_100km",
        4.5,
        {"market": "IT", "procedure": "WLTP", "cycle": "combined"},
    )
    data["observations"][-1]["value_max"] = 5.5
    publish(conn, data, tmp_path)
    row = conn.execute(
        "SELECT seats, consumption_l_100km FROM catalog_read_specs WHERE variant_key = 'metro-g1-ice'"
    ).fetchone()
    assert row == {"seats": None, "consumption_l_100km": None}
    assert (
        conn.execute(
            "SELECT value_max FROM catalog_current_facts WHERE metric = 'liquid_consumption_l_100km'"
        ).fetchone()["value_max"]
        == 5.5
    )


def test_adoption_preserves_ids_and_blocks_legacy_writes(conn, tmp_path):
    data = bundle(tmp_path)
    vehicle = conn.execute("SELECT * FROM vehicles ORDER BY id LIMIT 1").fetchone()
    spec = conn.execute(
        "SELECT * FROM vehicle_specs WHERE vehicle_id = %s", (vehicle["id"],)
    ).fetchone()
    data["vehicles"] = [
        {
            **data["vehicles"][0],
            **{
                k: vehicle[k]
                for k in (
                    "canonical_key",
                    "model_family_key",
                    "make",
                    "model",
                    "model_year",
                    "market",
                    "body_style",
                )
            },
        }
    ]
    data["variants"] = [
        {
            **data["variants"][0],
            "variant_key": spec["variant_key"],
            "vehicle_key": vehicle["canonical_key"],
        }
    ]
    data["observations"] = data["decisions"] = []
    batch = stage_catalog_v2(
        conn, CatalogV2.model_validate(data), artifact_root=tmp_path
    )
    with pytest.raises(CatalogValidationError, match="adopt-legacy"):
        publish_catalog_v2(conn, batch, artifact_root=tmp_path)
    assert (
        publish_catalog_v2(conn, batch, artifact_root=tmp_path, adopt_legacy=True)
        == "published"
    )
    saved = conn.execute(
        "SELECT * FROM vehicle_specs WHERE id = %s", (spec["id"],)
    ).fetchone()
    assert saved["legacy_record"]["horsepower"] == spec["horsepower"]
    assert (
        conn.execute(
            "SELECT spec_id FROM listings WHERE vehicle_id = %s", (vehicle["id"],)
        ).fetchone()["spec_id"]
        == spec["id"]
    )
    read = conn.execute(
        "SELECT horsepower, battery_kwh, seats FROM catalog_read_specs WHERE id = %s",
        (spec["id"],),
    ).fetchone()
    assert all(value is None for value in read.values())
    conn.execute("SELECT set_config('drivewise.catalog_writer', '', true)")
    with pytest.raises(psycopg.errors.CheckViolation, match="v2 publisher"):
        with conn.transaction():
            conn.execute(
                "UPDATE vehicle_specs SET seats = 6 WHERE id = %s", (spec["id"],)
            )


def test_analysis_does_not_invent_unknown_age_or_use_unreviewed_seed(conn, tmp_path):
    publish(conn, bundle(tmp_path), tmp_path)
    candidates = AdvisorRepository(conn).list_model_analysis_candidates()
    assert all(not c["listings"] for c in candidates)
    assert all(s["consumption_l_100km"] is None for c in candidates for s in c["specs"])
    unknown = next(c for c in candidates if c["vehicle"]["model_year"] is None)
    result = build_model_analysis(
        ModelAnalysisRequest(
            vehicle_id=unknown["vehicle"]["id"],
            current_km=10000,
            analysis_scope=["maintenance"],
        ),
        candidates,
        as_of=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )
    assert result.estimated_costs.estimated_annual_maintenance_eur is None
    assert "maintenance_inputs" in result.missing_data


def test_permitted_facts_feed_both_consumers_and_revocation_removes_them(
    conn, tmp_path
):
    data = bundle(tmp_path)
    data["variants"][0].update(
        engine_code="ACME-ICE-1",
        valid_from="2025-01-01",
        valid_to="2027-12-31",
        external_references=[{"namespace": "manufacturer", "value": "ACME-001"}],
    )
    data["sources"][0]["ranking_permission"] = "permitted"
    data["snapshots"][0]["evidence_kind"] = "sourced"
    add_fact(data, "seats", 5)
    add_fact(
        data,
        "cargo_volume_liters",
        300,
        {"market": "IT", "method": "VDA", "seating_configuration": "all_seats_up"},
    )
    add_fact(
        data,
        "liquid_consumption_l_100km",
        4.5,
        {"market": "IT", "procedure": "WLTP", "cycle": "combined"},
    )
    publish(conn, data, tmp_path)
    spec = conn.execute(
        "SELECT * FROM vehicle_specs WHERE variant_key = 'metro-g1-ice'"
    ).fetchone()
    expected_identity = {
        "powertrain_type": "ICE",
        "fuel": "petrol",
        "engine_code": "ACME-ICE-1",
        "valid_from": "2025-01-01",
        "valid_to": "2027-12-31",
        "external_references": [{"namespace": "manufacturer", "value": "ACME-001"}],
    }

    def identity(value):
        return VehicleSpec.model_validate(value).model_dump(
            mode="json", include=set(expected_identity)
        )

    detail_spec = VehicleDetail.model_validate(
        VehiclesRepository(conn).get_vehicle(spec["vehicle_id"])
    ).specs[0]
    assert identity(detail_spec) == expected_identity
    resolve_rows = VehiclesRepository(conn).list_resolve_candidates("IT")
    powertrains = {row["variant_key"]: row["powertrain_type"] for row in resolve_rows}
    assert powertrains["metro-g2-bev"] == "BEV"
    assert powertrains["metro-g2-phev"] == "PHEV"
    resolved_spec = next(
        row["spec"]
        for row in resolve_vehicle_query(
            VehicleResolveRequest(query="Acme Metro City"),
            resolve_rows,
        ).model_dump(mode="json")["matches"]
        if row["spec"] and row["spec"]["variant_key"] == spec["variant_key"]
    )
    assert identity(resolved_spec) == expected_identity
    run_id = uuid4()
    conn.execute(
        "INSERT INTO import_runs (id,schema_version,dataset_hash,file_name,status) VALUES (%s,1,'offer-test','test','completed')",
        (run_id,),
    )
    source_id = conn.execute(
        "SELECT id FROM sources WHERE source_key = 'synthetic-v2'"
    ).fetchone()["id"]
    listing_id = uuid4()
    conn.execute(
        """INSERT INTO listings (id,vehicle_id,spec_id,source_id,listing_ref,title,price_eur,
                   mileage,condition,source_url,first_seen_at,last_seen_at,content_hash,import_run_id)
                   VALUES (%s,%s,%s,%s,'test','Test offer',10000,10000,'used','https://example.test/offer',now(),now(),'test',%s)""",
        (listing_id, spec["vehicle_id"], spec["id"], source_id, run_id),
    )
    listing_repo = ListingsRepository(conn)
    listing_spec = ListingWithVehicle.model_validate(
        listing_repo.get_listing(listing_id)
    ).spec
    assert listing_spec is not None
    assert identity(listing_spec) == expected_identity
    assert (
        identity(
            listing_repo.list_listings(ListingFilters(spec_id=spec["id"]))[0]["spec"]
        )
        == expected_identity
    )
    repo = AdvisorRepository(conn)
    candidates = repo.list_candidates()
    assert len(candidates) == 1
    assert identity(candidates[0]["spec"]) == expected_identity
    assert candidates[0]["spec"]["consumption_l_100km"] == 4.5
    items = build_recommendations(
        AdvisorRecommendationRequest(budget_max_eur=15000, primary_use="city"),
        candidates,
    )
    assert len(items) == 1 and items[0].vehicle.catalog_version == 2
    assert items[0].selected_spec.catalog_version == 2
    assert identity(items[0].selected_spec) == expected_identity
    assert any(p.decision_id for p in items[0].provenance if p.metric == "seats")
    recommendation_id = repo.create_run({})
    repo.save_items(recommendation_id, items)
    saved = conn.execute(
        "SELECT score_breakdown FROM recommendation_items WHERE run_id = %s",
        (recommendation_id,),
    ).fetchone()["score_breakdown"]
    assert any(p["decision_id"] for p in saved["provenance"] if p["metric"] == "seats")
    analysis = next(
        c
        for c in repo.list_model_analysis_candidates()
        if c["vehicle"]["id"] == spec["vehicle_id"]
    )
    assert analysis["listings"][0]["price_eur"] == 10000
    assert identity(analysis["specs"][0]) == expected_identity
    assert analysis["specs"][0]["consumption_l_100km"] == 4.5
    conn.execute(
        "UPDATE listings SET last_seen_at = now() - interval '40 days', first_seen_at = now() - interval '50 days' WHERE id = %s",
        (listing_id,),
    )
    assert not repo.list_candidates()
    assert all(not c["listings"] for c in repo.list_model_analysis_candidates())
    conn.execute(
        "UPDATE sources SET ranking_permission = 'not_permitted' WHERE id = %s",
        (source_id,),
    )
    analysis = next(
        c
        for c in repo.list_model_analysis_candidates()
        if c["vehicle"]["id"] == spec["vehicle_id"]
    )
    assert analysis["specs"][0]["consumption_l_100km"] is None
    assert analysis["specs"][0]["fuel_type"] is None
    assert not repo.list_candidates()


def test_publish_rechecks_artifacts_and_identity_collision_rolls_back(conn, tmp_path):
    data = bundle(tmp_path)
    batch = stage_catalog_v2(
        conn, CatalogV2.model_validate(data), artifact_root=tmp_path
    )
    (tmp_path / data["snapshots"][0]["artifact_path"]).write_text(
        "changed after staging"
    )
    with pytest.raises(CatalogValidationError):
        publish_catalog_v2(conn, batch, artifact_root=tmp_path)
    assert (
        conn.execute("SELECT count(*) AS n FROM source_snapshots").fetchone()["n"] == 0
    )
    data = bundle(tmp_path)
    publish_catalog_v2(conn, batch, artifact_root=tmp_path)
    data["vehicles"][0]["canonical_key"] = "duplicate-identity"
    data["variants"][0]["vehicle_key"] = "duplicate-identity"
    bad = stage_catalog_v2(conn, CatalogV2.model_validate(data), artifact_root=tmp_path)
    with pytest.raises(psycopg.errors.UniqueViolation):
        publish_catalog_v2(conn, bad, artifact_root=tmp_path)
    assert (
        conn.execute(
            "SELECT count(*) AS n FROM vehicles WHERE make = 'Acme'"
        ).fetchone()["n"]
        == 3
    )


def test_upgrade_collision_check_precedes_identity_constraint_replacement(conn):
    schema = f"v2_collision_{uuid4().hex}"
    with conn.transaction(force_rollback=True):
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(
            sql.SQL("SET LOCAL search_path TO {}, public").format(
                sql.Identifier(schema)
            )
        )
        for migration in sorted(MIGRATIONS_PATH.glob("*.sql")):
            if migration.name[:4] not in {"0001", "0009"}:
                conn.execute(migration.read_text())
        conn.execute(
            """INSERT INTO vehicles (id, canonical_key, model_family_key, make, model,
                        model_year, market, body_style, fuel_type)
                        SELECT %s, 'case-collision', model_family_key, upper(make), model,
                        model_year, market, body_style, fuel_type FROM vehicles ORDER BY id LIMIT 1""",
            (uuid4(),),
        )
        with pytest.raises(psycopg.errors.UniqueViolation):
            with conn.transaction():
                conn.execute(
                    (MIGRATIONS_PATH / "0009_catalog_publication.sql").read_text()
                )
        assert conn.execute(
            "SELECT 1 FROM pg_constraint WHERE conname = 'vehicles_make_model_model_year_market_key' AND conrelid = 'vehicles'::regclass"
        ).fetchone()
        assert (
            conn.execute(
                "SELECT count(*) AS n FROM information_schema.columns WHERE table_schema = %s AND table_name = 'vehicles' AND column_name = 'catalog_version'",
                (schema,),
            ).fetchone()["n"]
            == 0
        )


def test_publication_migration_preserves_existing_knowledge_engine_codes(conn):
    schema = f"v2_knowledge_{uuid4().hex}"
    with conn.transaction(force_rollback=True):
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(
            sql.SQL("SET LOCAL search_path TO {}, public").format(
                sql.Identifier(schema)
            )
        )
        for migration in sorted(MIGRATIONS_PATH.glob("*.sql")):
            if migration.name[:4] not in {"0001", "0009"}:
                conn.execute(migration.read_text())
        conn.execute("ALTER TABLE vehicle_specs ADD COLUMN engine_code text")
        conn.execute("UPDATE vehicle_specs SET engine_code = 'reviewed-code'")
        conn.execute((MIGRATIONS_PATH / "0009_catalog_publication.sql").read_text())
        codes = conn.execute("SELECT engine_code FROM catalog_read_specs").fetchall()
        assert codes and all(row["engine_code"] == "reviewed-code" for row in codes)
