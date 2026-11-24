import decimal
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
# Synthetic price-list row; real manufacturer prices stay out of the repository.
LIST_PRICE_TERMS = {
    "printed_amount_eur": "100.00",
    "printed_basis": "incl_vat",
    "vat_rate_percent": None,
    "trim_label": "Synthetic Trim 50/68",
    "price_list_valid_from": "2026-01-01",
    "substitute_note": None,
}


# Synthetic turnkey row: 20,000.00 printed, on-road charge 1,000.00 + 22% VAT.
TURNKEY_TERMS = {
    **LIST_PRICE_TERMS,
    "printed_amount_eur": "20000.00",
    "printed_basis": "turnkey",
    "vat_rate_percent": "22",
    "on_road_charge_eur": "1000.00",
    "on_road_charge_includes_vat": False,
}
# Rows a direct INSERT must not store: each once made the Advisor return HTTP 500
# or would, because a missing key yields SQL UNKNOWN, which a CHECK accepts.
_BROKEN_SQL_TERMS = [
    {k: v for k, v in LIST_PRICE_TERMS.items() if k != "printed_basis"},
    {k: v for k, v in LIST_PRICE_TERMS.items() if k != "printed_amount_eur"},
    {k: v for k, v in LIST_PRICE_TERMS.items() if k != "price_list_valid_from"},
    {**LIST_PRICE_TERMS, "price_list_valid_from": "2026-02-30"},
    {**LIST_PRICE_TERMS, "price_list_valid_from": "not-a-date"},
    {**LIST_PRICE_TERMS, "printed_basis": None},
    {**LIST_PRICE_TERMS, "printed_basis": "gross"},
    {**LIST_PRICE_TERMS, "printed_amount_eur": "abc"},
    {**LIST_PRICE_TERMS, "printed_amount_eur": "NaN"},
    {**LIST_PRICE_TERMS, "trim_label": 42},
    {**LIST_PRICE_TERMS, "trim_label": "  "},
    {**LIST_PRICE_TERMS, "vat_rate_percent": "22"},
    {**LIST_PRICE_TERMS, "printed_basis": "excl_vat"},
    {**LIST_PRICE_TERMS, "printed_basis": "turnkey"},
    {**TURNKEY_TERMS, "on_road_charge_includes_vat": "yes"},
    {**TURNKEY_TERMS, "vat_rate_percent": None},
    # Half of the on-road pair on a price that is not turnkey.
    {**LIST_PRICE_TERMS, "on_road_charge_eur": "10.00"},
    {**LIST_PRICE_TERMS, "on_road_charge_includes_vat": True},
    # PostgreSQL reads 0x64 as 100; the API cannot parse it.
    {**LIST_PRICE_TERMS, "printed_amount_eur": "0x64"},
    {**TURNKEY_TERMS, "vat_rate_percent": "0x16"},
    {**TURNKEY_TERMS, "on_road_charge_eur": "0x3E8"},
    ["not", "an", "object"],
]
# (terms, VAT-inclusive value) pairs a direct INSERT accepts.
_VALID_SQL_TERMS = [
    # 10.25 x 1.22 = 12.505: the half-cent tie rounds up, as in Python.
    ({**LIST_PRICE_TERMS, "printed_amount_eur": "10.25", "printed_basis": "excl_vat",
      "vat_rate_percent": "22"}, "12.51"),
    # 20,000.00 - 1,000.00 x 1.22 = 18,780.00.
    (TURNKEY_TERMS, "18780.00"),
    ({**TURNKEY_TERMS, "vat_rate_percent": None, "on_road_charge_eur": "900.50",
      "on_road_charge_includes_vat": True}, "19099.50"),
    # A JSON number is as good as a decimal string.
    ({**LIST_PRICE_TERMS, "printed_amount_eur": 100}, "100.00"),
]


def test_v2_represents_identity_uncertainty_and_keeps_conflict_history():
    payload = load_catalog_v2(FIXTURE)
    first, second, unknown_year = payload.vehicles[:3]
    assert first.model == second.model and first.model_year == second.model_year
    assert first.generation_key != second.generation_key
    assert unknown_year.model_year is None
    assert payload.variants[1].trim == payload.variants[2].trim
    assert payload.variants[1].powertrain_type != payload.variants[2].powertrain_type
    length = next(o for o in payload.observations if o.metric == "length_mm")
    assert length.value_max > length.value_min
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
            # 0010 only extends the 0008 metric registry, so it applies here too.
            conn.execute((MIGRATIONS_PATH / "0010_two_wheel_metrics.sql").read_text())
            conn.execute((MIGRATIONS_PATH / "0011_list_price_metric.sql").read_text())
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
                    list_price=(
                        Jsonb(LIST_PRICE_TERMS) if metric == "list_price_eur" else None
                    ),
                )
                if metric == "list_price_eur":
                    observation.update(value_min=Decimal("100.00"), value_max=Decimal("100.00"))
                    # Terms are required for a list price and refused on any other metric.
                    for broken in [
                        {"list_price": None},
                        {"value_max": Decimal("101.00")},
                        *(
                            {"list_price": Jsonb(terms)}
                            for terms in _BROKEN_SQL_TERMS
                        ),
                    ]:
                        with pytest.raises(psycopg.errors.CheckViolation):
                            with conn.transaction():
                                insert(
                                    conn,
                                    "spec_observations",
                                    {**observation, "id": uuid4(), **broken},
                                )
                    # The SQL twin accepts what the contract accepts, cent for cent.
                    for terms, value in _VALID_SQL_TERMS:
                        insert(
                            conn,
                            "spec_observations",
                            {
                                **observation,
                                "id": uuid4(),
                                "list_price": Jsonb(terms),
                                "value_min": Decimal(value),
                                "value_max": Decimal(value),
                            },
                        )
                elif metric == "seats":
                    with pytest.raises(psycopg.errors.CheckViolation):
                        with conn.transaction():
                            insert(
                                conn,
                                "spec_observations",
                                {
                                    **observation,
                                    "id": uuid4(),
                                    "list_price": Jsonb(LIST_PRICE_TERMS),
                                },
                            )
                insert(conn, "spec_observations", observation)
                with pytest.raises(psycopg.errors.CheckViolation):
                    with conn.transaction():
                        insert(
                            conn,
                            "spec_observations",
                            {**observation, "id": uuid4(), "unit": "wrong"},
                        )


def test_v2_fixture_covers_two_wheelers_and_enforces_their_units():
    payload = load_catalog_v2(FIXTURE)
    assert {v.vehicle_type for v in payload.vehicles} == {
        "car",
        "motorcycle",
        "scooter",
    }
    assert {"seat_height_mm", "fuel_tank_capacity_liters", "underseat_storage_liters"} <= {
        o.metric for o in payload.observations
    }
    for metric, wrong_unit in [
        ("seat_height_mm", "cm"),
        ("underseat_storage_liters", "dm3"),
    ]:
        raw = json.loads(FIXTURE.read_text())
        observation = next(o for o in raw["observations"] if o["metric"] == metric)
        observation["unit"] = wrong_unit
        with pytest.raises(ValidationError, match=f"{metric} requires unit"):
            CatalogV2.model_validate(raw)
    # Wet weight is mass_kg with its definition, never an undefined mass.
    raw = json.loads(FIXTURE.read_text())
    mass = next(o for o in raw["observations"] if o["metric"] == "mass_kg")
    assert mass["context"]["method"] == "wet"
    del mass["context"]["method"]
    with pytest.raises(ValidationError, match="mass requires"):
        CatalogV2.model_validate(raw)


def _list_price_bundle(terms: dict, value: str) -> dict:
    raw = json.loads(FIXTURE.read_text())
    observation = dict(raw["observations"][0])
    observation.update(
        id=str(uuid4()),
        metric="list_price_eur",
        raw_value=terms["printed_amount_eur"],
        raw_unit="EUR",
        value_min=value,
        value_max=value,
        unit="EUR",
        list_price=terms,
    )
    raw["observations"].append(observation)
    return raw


def test_list_price_carries_its_terms_and_vat_inclusive_value():
    printed = CatalogV2.model_validate(
        _list_price_bundle(LIST_PRICE_TERMS, "100.00")
    ).observations[-1]
    assert printed.list_price.computed_from_excl_vat is False
    computed_terms = {
        **LIST_PRICE_TERMS,
        "printed_amount_eur": "10000.01",
        "printed_basis": "excl_vat",
        "vat_rate_percent": "22",
        "substitute_note": "Registered version no longer listed; nearest current row.",
    }
    # 10000.01 x 1.22 = 12200.0122, stored to the cent.
    computed = CatalogV2.model_validate(
        _list_price_bundle(computed_terms, "12200.01")
    ).observations[-1]
    assert computed.list_price.computed_from_excl_vat is True
    assert computed.list_price.substitute_note
    for terms, value, message in [
        (computed_terms, "10000.01", "VAT-inclusive amount"),
        ({**computed_terms, "vat_rate_percent": None}, "12200.01", "VAT rate"),
        ({**LIST_PRICE_TERMS, "vat_rate_percent": "22"}, "100.00", "VAT rate"),
        ({**LIST_PRICE_TERMS, "printed_amount_eur": "100.001"}, "100.001", "two decimals"),
        ({**LIST_PRICE_TERMS, "trim_label": ""}, "100.00", "at least 1 character"),
    ]:
        with pytest.raises(ValidationError, match=message):
            CatalogV2.model_validate(_list_price_bundle(terms, value))
    raw = _list_price_bundle(LIST_PRICE_TERMS, "100.00")
    raw["observations"][-1]["list_price"] = None
    with pytest.raises(ValidationError, match="list price terms are required"):
        CatalogV2.model_validate(raw)
    raw = json.loads(FIXTURE.read_text())
    raw["observations"][0]["list_price"] = LIST_PRICE_TERMS
    with pytest.raises(ValidationError, match="list price terms are required"):
        CatalogV2.model_validate(raw)


def test_turnkey_list_price_keeps_the_printed_row_and_stores_the_list_price():
    # ADR-015: turnkey price minus the stated on-road charge, marked as computed.
    observation = CatalogV2.model_validate(
        _list_price_bundle(TURNKEY_TERMS, "18780.00")
    ).observations[-1]
    terms = observation.list_price
    assert terms.derivation == "computed_from_turnkey"
    assert terms.computed_from_excl_vat is False
    assert terms.printed_amount_eur == Decimal("20000.00")
    assert terms.on_road_charge_incl_vat() == Decimal("1220.00")
    dumped = observation.model_dump(mode="json")["list_price"]
    assert dumped["on_road_charge_eur"] == "1000.00"
    assert dumped["on_road_charge_includes_vat"] is False
    with_vat_charge = {
        **TURNKEY_TERMS,
        "vat_rate_percent": None,
        "on_road_charge_eur": "900.50",
        "on_road_charge_includes_vat": True,
    }
    assert CatalogV2.model_validate(
        _list_price_bundle(with_vat_charge, "19099.50")
    ).observations[-1].list_price.incl_vat_amount() == Decimal("19099.50")
    for terms, value, message in [
        (TURNKEY_TERMS, "20000.00", "VAT-inclusive amount"),
        ({**TURNKEY_TERMS, "on_road_charge_eur": None}, "18780.00", "on-road charge"),
        (
            {**TURNKEY_TERMS, "on_road_charge_includes_vat": None},
            "18780.00",
            "on-road charge",
        ),
        ({**TURNKEY_TERMS, "vat_rate_percent": None}, "18780.00", "VAT rate"),
        ({**with_vat_charge, "vat_rate_percent": "22"}, "19099.50", "VAT rate"),
        (
            {**TURNKEY_TERMS, "on_road_charge_eur": "17000.00"},
            "-740.00",
            "below the turnkey price",
        ),
        (
            {**LIST_PRICE_TERMS, "on_road_charge_eur": "10.00"},
            "100.00",
            "on-road charge",
        ),
    ]:
        with pytest.raises(ValidationError, match=message):
            CatalogV2.model_validate(_list_price_bundle(terms, value))
    # Terms without an on-road charge serialize exactly as before turnkey existed.
    assert set(
        CatalogV2.model_validate(_list_price_bundle(LIST_PRICE_TERMS, "100.00"))
        .observations[-1]
        .model_dump(mode="json")["list_price"]
    ) == set(LIST_PRICE_TERMS)


@pytest.mark.parametrize("rounding", [decimal.ROUND_HALF_EVEN, decimal.ROUND_DOWN])
def test_list_price_rounding_ignores_the_callers_decimal_context(rounding):
    terms = {
        **LIST_PRICE_TERMS,
        "printed_amount_eur": "10.25",
        "printed_basis": "excl_vat",
        "vat_rate_percent": "22",
    }
    # 10.25 x 1.22 = 12.505: a tie, always rounded half up to 12.51.
    with decimal.localcontext(decimal.Context(prec=3, rounding=rounding)):
        observation = CatalogV2.model_validate(
            _list_price_bundle(terms, "12.51")
        ).observations[-1]
        assert observation.list_price.incl_vat_amount() == Decimal("12.51")


@pytest.mark.parametrize("amount", ["1e27", "1e400", "10000000000.00"])
def test_out_of_range_list_price_is_a_validation_error(amount):
    for terms in [
        {**LIST_PRICE_TERMS, "printed_amount_eur": amount},
        {**LIST_PRICE_TERMS, "printed_amount_eur": amount, "printed_basis": "excl_vat",
         "vat_rate_percent": "22"},
        {**TURNKEY_TERMS, "on_road_charge_eur": amount},
    ]:
        with pytest.raises(ValidationError, match="below 10\\^10"):
            CatalogV2.model_validate(_list_price_bundle(terms, "100.00"))


# Recorded on 2026-11-24 by staging the shipped fixture with the pre-list-price
# code (commit 44988f4) into a disposable database: catalog_v2_batches.dataset_hash.
PRE_UPGRADE_FIXTURE_DIGEST = (
    "51fe270a979d39964f2780cf5531dab1f091c6276d7db638dd4fb55d2ba77a44"
)


def test_a_bundle_staged_before_list_prices_keeps_its_dataset_hash():
    from app.ingestion.catalog_v2_writer import dataset_hash

    payload = load_catalog_v2(FIXTURE)
    data = payload.model_dump(mode="json")
    assert all("list_price" not in observation for observation in data["observations"])
    # Re-staging that bundle finds the published batch instead of adding a second one.
    assert dataset_hash(data) == PRE_UPGRADE_FIXTURE_DIGEST
