import importlib.util
import json
import os
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.db.migrations import MIGRATIONS_PATH, run_migrations
from app.ingestion.catalog import CatalogValidationError, load_catalog
from app.ingestion.catalog_v2 import CatalogV2, METRIC_UNITS, load_catalog_v2


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "data/fixtures/catalog/catalog-v2.synthetic.json"


def test_v2_represents_identity_uncertainty_and_keeps_conflict_history():
    payload = load_catalog_v2(FIXTURE)
    first, second, unknown_year = payload.vehicles
    assert first.model == second.model and first.model_year == second.model_year
    assert first.generation_key != second.generation_key
    assert unknown_year.model_year is None
    assert payload.variants[1].trim == payload.variants[2].trim
    assert payload.variants[1].powertrain_type != payload.variants[2].powertrain_type
    assert payload.observations[-1].value_max > payload.observations[-1].value_min
    assert payload.decisions[1].supersedes_id == payload.decisions[0].id
    assert payload.decisions[0].status == "verified"
    assert payload.decisions[1].status == "conflicted"
    assert payload.decisions[1].selected_observation_id is None
    assert payload.decisions[2].status == "unknown"
    assert not payload.decisions[2].evidence_ids
    assert json.loads((ROOT / "docs/catalog-v2.schema.json").read_text()) == (
        CatalogV2.model_json_schema()
    )


def test_v2_preserves_decimal_precision_from_json_and_round_trip(tmp_path):
    raw = FIXTURE.read_text().replace(
        '"value_min": 64', '"value_min": 1.0000000000000001', 1
    )
    path = tmp_path / "precise.json"
    path.write_text(raw)
    payload = load_catalog_v2(path)
    value = payload.observations[0].value_min
    assert value == Decimal("1.0000000000000001")
    assert (
        CatalogV2.model_validate(payload.model_dump(mode="json"))
        .observations[0]
        .value_min
        == value
    )


def test_v2_rejects_duplicate_snapshot_storage_identity():
    raw = json.loads(FIXTURE.read_text())
    duplicate = {**raw["snapshots"][0], "id": str(uuid4())}
    raw["snapshots"].append(duplicate)
    with pytest.raises(ValidationError, match="duplicate snapshot acquisition"):
        CatalogV2.model_validate(raw)
    duplicate["retrieved_at"] = raw["snapshots"][1]["retrieved_at"]
    CatalogV2.model_validate(raw)


@pytest.mark.parametrize(
    ("section", "index", "field", "value", "message"),
    [
        ("observations", 0, "unit", "Wh", "requires unit"),
        ("observations", 0, "value_min", True, "Decimal input"),
        ("observations", 0, "value_min", float("nan"), "finite number"),
        ("observations", 0, "value_max", float("inf"), "finite number"),
        ("observations", 0, "value_min", 0, "zero is not unknown"),
        ("observations", 0, "value_max", 1, "precedes value_min"),
        ("observations", 0, "metric", "decision_score", "Input should be"),
        ("observations", 0, "snapshot_id", str(uuid4()), "unknown snapshot"),
        ("observations", 0, "variant_key", "missing", "unknown variant"),
        ("variants", 3, "fuel", "petrol", "BEV cannot"),
        ("vehicles", 0, "market", "EU", "national market"),
        ("snapshots", 0, "artifact_path", "../../.env", "relative path"),
        ("snapshots", 0, "retrieved_at", "2026-09-01T12:00:00", "timezone"),
        ("decisions", 0, "selected_observation_id", None, "must select"),
        ("decisions", 1, "supersedes_id", None, "revision chain"),
        ("decisions", 1, "decided_at", "2026-08-01T12:00:00Z", "predates"),
        ("decisions", 1, "evidence_ids", [str(UUID(int=11))], "competing"),
    ],
)
def test_v2_rejects_invalid_evidence(section, index, field, value, message):
    raw = json.loads(FIXTURE.read_text())
    raw[section][index][field] = value
    with pytest.raises(ValidationError, match=message):
        CatalogV2.model_validate(raw)


def test_v2_rejects_duplicate_identity_even_with_unknown_attributes():
    raw = json.loads(FIXTURE.read_text())
    duplicate = {**raw["vehicles"][2], "canonical_key": "different-import-key"}
    raw["vehicles"].append(duplicate)
    with pytest.raises(ValidationError, match="duplicate vehicle identity"):
        CatalogV2.model_validate(raw)


def test_unknown_and_not_applicable_are_explicit_and_do_not_invent_values():
    raw = json.loads(FIXTURE.read_text())
    raw["decisions"][2].update(
        variant_key="metro-g1-ice",
        metric="battery_usable_kwh",
        status="not_applicable",
        reason="Synthetic ICE configuration has no traction battery.",
    )
    payload = CatalogV2.model_validate(raw)
    assert payload.decisions[2].selected_observation_id is None
    raw["variants"][3]["valid_from"] = "2026-01-01"
    raw["observations"][0]["context"]["valid_to"] = "2025-12-31"
    with pytest.raises(ValidationError, match="does not overlap"):
        CatalogV2.model_validate(raw)


@pytest.mark.parametrize("status", ["unknown", "not_applicable"])
def test_decisions_without_observations_still_require_applicable_dates(status):
    raw = json.loads(FIXTURE.read_text())
    raw["variants"][4]["valid_from"] = "2026-01-01"
    raw["decisions"][2]["status"] = status
    raw["decisions"][2]["context"]["valid_to"] = "2025-12-31"
    with pytest.raises(ValidationError, match="decision validity does not overlap"):
        CatalogV2.model_validate(raw)


def test_context_size_accounts_for_multibyte_text_and_storage_keys():
    raw = json.loads(FIXTURE.read_text())
    context = raw["observations"][0]["context"]
    context["method"] = "".join(chr(0x4E00 + i) for i in range(200))
    context["seating_configuration"] = "".join(chr(0x5200 + i) for i in range(200))
    CatalogV2.model_validate(raw)
    context["method"] = "".join(chr(0x4E00 + i) for i in range(500))
    context["seating_configuration"] = "".join(chr(0x5200 + i) for i in range(500))
    with pytest.raises(ValidationError, match="1800 UTF-8 bytes"):
        CatalogV2.model_validate(raw)


@pytest.mark.parametrize("change", ["gross", "market", "candidate", "cycle"])
def test_decision_cannot_verify_a_different_fact(change):
    raw = json.loads(FIXTURE.read_text())
    if change == "gross":
        raw["decisions"][0]["selected_observation_id"] = str(UUID(int=10))
        raw["decisions"][0]["evidence_ids"] = [str(UUID(int=10))]
    elif change == "market":
        raw["observations"][1]["context"]["market"] = "DE"
    elif change == "candidate":
        raw["observations"][1]["variant_key"] = None
        raw["observations"][1]["candidate_variant_keys"] = ["metro-g2-bev"]
    else:
        raw["observations"][1]["context"]["cycle"] = "urban"
    with pytest.raises(ValidationError, match="different|differs"):
        CatalogV2.model_validate(raw)


def test_phev_measurement_requires_explicit_context_before_verification():
    raw = json.loads(FIXTURE.read_text())
    observation = raw["observations"][5]
    decision = {
        **raw["decisions"][0],
        "id": str(uuid4()),
        "variant_key": "metro-g2-phev",
        "metric": observation["metric"],
        "context": observation["context"].copy(),
        "selected_observation_id": observation["id"],
        "evidence_ids": [observation["id"]],
    }
    raw["decisions"].append(decision)
    CatalogV2.model_validate(raw)
    observation["context"]["battery_condition"] = "unknown"
    decision["context"]["battery_condition"] = "unknown"
    with pytest.raises(ValidationError, match="battery condition"):
        CatalogV2.model_validate(raw)
    observation["context"].pop("procedure")
    with pytest.raises(ValidationError, match="require procedure"):
        CatalogV2.model_validate(raw)


def test_v2_check_is_offline_and_v1_writer_rejects_v2(monkeypatch, capsys, tmp_path):
    import psycopg

    def unexpected_connection(*args, **kwargs):
        pytest.fail("Contract validation must not connect to a database")

    monkeypatch.setattr(psycopg, "connect", unexpected_connection)
    spec = importlib.util.spec_from_file_location(
        "check_catalog_v2", ROOT / "apps/api/scripts/check_catalog_v2.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main(["--path", str(FIXTURE)]) == 0
    assert "Catalog v2 valid" in capsys.readouterr().out
    with pytest.raises(CatalogValidationError):
        load_catalog(FIXTURE)
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"schema_version": 2, broken')
    assert module.main(["--path", str(invalid)]) == 1
    assert "Catalog v2 rejected" in capsys.readouterr().err


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)
def test_evidence_migration_preserves_catalog_and_enforces_history():
    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb

    database_url = os.environ["TEST_DATABASE_URL"]
    run_migrations(database_url)
    assert run_migrations(database_url).applied == []
    schema = f"evidence_test_{uuid4().hex}"

    def insert(conn, table, record):
        conn.execute(
            sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table),
                sql.SQL(", ").join(map(sql.Identifier, record)),
                sql.SQL(", ").join(sql.Placeholder() for _ in record),
            ),
            list(record.values()),
        )

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        # All schema/data changes in this test are rolled back, including triggers.
        with conn.transaction(force_rollback=True):
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            conn.execute(
                sql.SQL("SET LOCAL search_path TO {}, public").format(
                    sql.Identifier(schema)
                )
            )
            for name in [
                "0002_create_mvp_schema.sql",
                "0003_seed_initial_vehicles.sql",
                "0004_curated_catalog.sql",
            ]:
                conn.execute((MIGRATIONS_PATH / name).read_text())
            before = conn.execute(
                "SELECT id, variant_key, horsepower, battery_kwh FROM vehicle_specs ORDER BY id"
            ).fetchall()
            conn.execute((MIGRATIONS_PATH / "0008_catalog_evidence.sql").read_text())
            assert (
                conn.execute(
                    "SELECT id, variant_key, horsepower, battery_kwh FROM vehicle_specs ORDER BY id"
                ).fetchall()
                == before
            )
            assert (
                conn.execute(
                    "SELECT count(*) AS n FROM vehicles WHERE generation_key IS NOT NULL OR vehicle_type IS NOT NULL"
                ).fetchone()["n"]
                == 0
            )
            spec_id = before[-1]["id"]
            other_spec_id = before[0]["id"]
            source_id = conn.execute("SELECT id FROM sources LIMIT 1").fetchone()["id"]
            payload = load_catalog_v2(FIXTURE)
            for snapshot in payload.snapshots:
                record = snapshot.model_dump()
                record.pop("source_key")
                record["source_url"] = str(record.pop("url"))
                insert(conn, "source_snapshots", {**record, "source_id": source_id})
            for observation in payload.observations[:3]:
                record = observation.model_dump()
                record.pop("variant_key")
                record["candidate_variant_keys"] = Jsonb(
                    record["candidate_variant_keys"]
                )
                record["context"] = Jsonb(observation.context.model_dump(mode="json"))
                insert(conn, "spec_observations", {**record, "spec_id": spec_id})
            large_context = payload.observations[0].context.model_dump(mode="json")
            large_context.update(
                method="".join(chr(0x4E00 + i) for i in range(200)),
                seating_configuration="".join(chr(0x5200 + i) for i in range(200)),
            )
            insert(
                conn,
                "spec_observations",
                {
                    **record,
                    "id": uuid4(),
                    "spec_id": spec_id,
                    "context": Jsonb(large_context),
                },
            )
            large_context.update(
                method="".join(chr(0x4E00 + i) for i in range(500)),
                seating_configuration="".join(chr(0x5200 + i) for i in range(500)),
            )
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    insert(
                        conn,
                        "spec_observations",
                        {
                            **record,
                            "id": uuid4(),
                            "spec_id": spec_id,
                            "context": Jsonb(large_context),
                        },
                    )
            for decision in payload.decisions[:2]:
                record = decision.model_dump()
                record.pop("variant_key")
                record["context"] = Jsonb(decision.context.model_dump(mode="json"))
                insert(conn, "fact_decisions", {**record, "spec_id": spec_id})
            states = conn.execute(
                "SELECT status FROM fact_decisions ORDER BY decided_at"
            ).fetchall()
            assert [row["status"] for row in states] == ["verified", "conflicted"]
            for table in ["source_snapshots", "spec_observations", "fact_decisions"]:
                for statement in ["UPDATE {} SET id = id", "DELETE FROM {}"]:
                    with pytest.raises(psycopg.errors.CheckViolation):
                        with conn.transaction():
                            conn.execute(
                                sql.SQL(statement).format(sql.Identifier(table))
                            )

            decision = payload.decisions[0].model_dump()
            decision.pop("variant_key")
            decision.update(
                id=uuid4(),
                spec_id=spec_id,
                supersedes_id=UUID(int=21),
                decided_at=payload.decisions[1].decided_at,
            )
            decision["context"] = Jsonb(
                payload.decisions[0].context.model_dump(mode="json")
            )
            for override in [
                {"spec_id": other_spec_id},
                {"metric": "battery_gross_kwh"},
                {"evidence_ids": [UUID(int=11), UUID(int=11)]},
                {"evidence_ids": [UUID(int=11), uuid4()]},
                {"context": Jsonb({"market": "DE"})},
            ]:
                with pytest.raises(psycopg.IntegrityError):
                    with conn.transaction():
                        insert(conn, "fact_decisions", {**decision, **override})
            insert(conn, "fact_decisions", decision)
            with pytest.raises(psycopg.errors.UniqueViolation):
                with conn.transaction():
                    insert(conn, "fact_decisions", {**decision, "id": uuid4()})
            for metric, unit in METRIC_UNITS.items():
                # Exercise every SQL metric/unit pair, not just the fixture's battery.
                observation = payload.observations[0].model_dump()
                observation.pop("variant_key")
                observation.update(
                    id=uuid4(),
                    spec_id=spec_id,
                    metric=metric,
                    unit=unit,
                    context=Jsonb(
                        {
                            "market": "IT",
                            "procedure": "WLTP",
                            "cycle": "combined",
                            "method": "synthetic",
                            "seating_configuration": "all seats up",
                        }
                    ),
                    candidate_variant_keys=Jsonb([]),
                )
                insert(conn, "spec_observations", observation)
                with pytest.raises(psycopg.errors.CheckViolation):
                    with conn.transaction():
                        insert(
                            conn,
                            "spec_observations",
                            {**observation, "id": uuid4(), "unit": "wrong"},
                        )
