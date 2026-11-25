"""Migration 0015 (v2 read-view pivot), the migration lock and repository hardening."""

import os
import threading
import time
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row

from app.db import migrations
from app.db.migrations import MIGRATIONS_PATH, run_migrations
from app.repositories.advisor import AdvisorRepository
from app.repositories.documents import DocumentsRepository
from app.repositories.filters import DocumentFilters, ListingFilters, VehicleFilters
from app.repositories.listings import ListingsRepository
from app.repositories.vehicles import VehiclesRepository, contains_pattern
from app.schemas.listings import ListingWithVehicle
from app.schemas.vehicles import VehicleDetail
from test_catalog_v2_publication import (
    add_fact,
    add_list_price,
    bundle,
    publish,
    vehicle_id,
)


@pytest.fixture
def db():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    run_migrations(url)
    with psycopg.connect(url, row_factory=dict_row, autocommit=True) as connection:
        with connection.transaction(force_rollback=True):
            schema = f"council_views_{uuid4().hex}"
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


def permitted_bundle(tmp_path):
    data = bundle(tmp_path)
    # Simulated permitted source, not real vehicle data.
    data["sources"][0]["ranking_permission"] = "permitted"
    data["snapshots"][0]["evidence_kind"] = "sourced"
    return data


def wltp(**extra):
    return {"market": "IT", "procedure": "WLTP", "cycle": "combined", **extra}


def vda():
    return {"market": "IT", "method": "VDA", "seating_configuration": "all_seats_up"}


def add_unit_fact(data, metric, value, context, unit, variant="metro-g1-ice"):
    decision = add_fact(data, metric, value, context, variant=variant)
    data["observations"][-1].update(unit=unit, raw_unit=unit)
    return decision


def add_interval(data, metric, low, high, context, variant="metro-g1-ice"):
    decision = add_fact(data, metric, low, context, variant=variant)
    data["observations"][-1]["value_max"] = high
    return decision


def create_0012_views(conn):
    """The 0012 definitions of the two rewritten views, under legacy_* names."""
    text = (MIGRATIONS_PATH / "0012_list_price_read_view.sql").read_text()
    text = text.split("CREATE OR REPLACE VIEW catalog_analysis_specs")[0]
    text = text.replace(
        "CREATE OR REPLACE VIEW catalog_scalar_facts", "CREATE VIEW legacy_scalar_facts"
    ).replace("CREATE OR REPLACE VIEW catalog_read_specs", "CREATE VIEW legacy_read_specs")
    conn.execute(text.replace("FROM catalog_scalar_facts", "FROM legacy_scalar_facts"))


def assert_same_rows(conn, left, right, columns="*"):
    for first, second in ((left, right), (right, left)):
        extra = conn.execute(
            f"SELECT {columns} FROM {first} EXCEPT ALL SELECT {columns} FROM {second}"
        ).fetchall()
        assert extra == [], f"{first} has rows {second} lacks"


# Columns 0015 newly fills for v2 rows; every other column must be unchanged.
V2_DETAIL_COLUMNS = {"length_mm", "width_mm", "height_mm", "displacement_cc", "power_kw"}


def test_pivot_views_match_0012_semantics(db, tmp_path):
    data = permitted_bundle(tmp_path)
    add_fact(data, "seats", 5)
    add_fact(data, "cargo_volume_liters", 300, vda())
    # A cargo volume measured with the rear seats folded is not the VDA read value.
    add_fact(data, "cargo_volume_liters", 900,
             {"market": "IT", "method": "VDA", "seating_configuration": "rear_folded"},
             variant="metro-g2-hev")
    add_interval(data, "liquid_consumption_l_100km", 4.4, 4.9, wltp())
    # A PHEV consumption is never a scalar read value.
    add_unit_fact(data, "electric_consumption_kwh_100km", 15.2,
                  wltp(battery_condition="charge_depleting"), "kWh/100km",
                  variant="metro-g2-phev")
    add_unit_fact(data, "co2_g_km", 104, wltp(), "g/km")
    add_list_price(data)
    # Two current contexts of one metric: neither may be projected.
    add_fact(data, "seats", 4, variant="metro-g2-hev")
    add_fact(data, "seats", 5, {"market": "IT", "configuration_key": "lwb"},
             variant="metro-g2-hev")
    # An interval that is not a consumption stays out of the scalar reads.
    add_interval(data, "length_mm", 4000, 4020, {"market": "IT"}, variant="metro-g2-hev")
    unknown = add_unit_fact(data, "co2_g_km", 99, wltp(), "g/km", variant="metro-g2-hev")
    unknown.update(status="unknown", selected_observation_id=None)
    publish(db, data, tmp_path)
    create_0012_views(db)

    published = db.execute("SELECT count(*) AS n FROM catalog_scalar_facts").fetchone()
    assert published["n"] >= 6
    assert_same_rows(db, "catalog_scalar_facts", "legacy_scalar_facts")
    columns = [
        row["attname"]
        for row in db.execute(
            "SELECT attname FROM pg_attribute WHERE attrelid = 'catalog_read_specs'::regclass"
            " AND attnum > 0 ORDER BY attnum"
        ).fetchall()
    ]
    unchanged = ", ".join(c for c in columns if c not in V2_DETAIL_COLUMNS)
    assert_same_rows(db, "catalog_read_specs", "legacy_read_specs", unchanged)
    # v1 rows are untouched in every column.
    assert_same_rows(
        db,
        "(SELECT * FROM catalog_read_specs WHERE catalog_version = 1) AS new_v1",
        "(SELECT * FROM legacy_read_specs WHERE catalog_version = 1) AS old_v1",
    )
    basis = db.execute(
        "SELECT consumption_l_100km, consumption_l_100km_basis FROM catalog_read_specs"
        " WHERE variant_key = 'metro-g1-ice'"
    ).fetchone()
    assert basis == {
        "consumption_l_100km": Decimal("4.9"),
        "consumption_l_100km_basis": "interval_upper",
    }


def test_view_columns_keep_0014_names_and_types(db):
    # CREATE OR REPLACE VIEW already refuses a changed type; this pins the order too.
    def shape(view):
        return db.execute(
            "SELECT attname, format_type(atttypid, atttypmod) AS type FROM pg_attribute"
            " WHERE attrelid = %s::regclass AND attnum > 0 ORDER BY attnum",
            (view,),
        ).fetchall()

    specs = {row["attname"]: row["type"] for row in shape("catalog_read_specs")}
    assert len(specs) == 57
    assert list(specs)[-2:] == [
        "consumption_l_100km_basis",
        "energy_consumption_kwh_100km_basis",
    ]
    assert {c: specs[c] for c in sorted(V2_DETAIL_COLUMNS)} == {
        "displacement_cc": "integer",
        "height_mm": "integer",
        "length_mm": "integer",
        "power_kw": "numeric",
        "width_mm": "integer",
    }
    facts = [row["attname"] for row in shape("catalog_scalar_facts")]
    assert "metric_contexts" not in facts
    assert facts[-3:] == ["legacy_metric", "scalar_value", "scalar_basis"]
    assert len(facts) == 27


def publish_dimensioned(db, tmp_path):
    data = permitted_bundle(tmp_path)
    add_fact(data, "seats", 5)
    add_fact(data, "cargo_volume_liters", 300, vda())
    add_fact(data, "liquid_consumption_l_100km", 4.5, wltp())
    add_list_price(data, substitute_note="Synthetic: nearest current row.")
    for metric, value in (
        ("length_mm", 4010),
        ("body_width_mm", 1750),
        ("height_mm", 1480.5),  # not a whole number: never published as an integer
        ("engine_power_kw", 74),
    ):
        add_fact(data, metric, value)
    add_unit_fact(data, "engine_displacement_cc", 999, None, "cm3")
    # A hybrid's engine is not its whole power; its system power is.
    add_fact(data, "engine_power_kw", 68, variant="metro-g2-hev")
    add_fact(data, "engine_power_kw", 100, variant="metro-g2-phev")
    add_fact(data, "system_power_kw", 180, variant="metro-g2-phev")
    publish(db, data, tmp_path)


def test_read_specs_publish_v2_dimensions_and_power(db, tmp_path):
    publish_dimensioned(db, tmp_path)
    rows = {
        row["variant_key"]: row
        for row in db.execute(
            "SELECT variant_key, length_mm, width_mm, height_mm, displacement_cc, power_kw"
            " FROM catalog_read_specs WHERE catalog_version = 2"
        ).fetchall()
    }
    assert rows["metro-g1-ice"] == {
        "variant_key": "metro-g1-ice",
        "length_mm": 4010,
        "width_mm": 1750,
        "height_mm": None,
        "displacement_cc": 999,
        "power_kw": Decimal("74"),
    }
    assert rows["metro-g2-hev"]["power_kw"] is None
    assert rows["metro-g2-phev"]["power_kw"] == Decimal("180")

    detail = VehiclesRepository(db).get_vehicle(vehicle_id(db, "metro-g1-2026"))
    VehicleDetail.model_validate(detail)
    spec = next(s for s in detail["specs"] if s["variant_key"] == "metro-g1-ice")
    assert spec["dimensions"]["width_mm"] == 1750
    assert spec["powertrain"]["power_kw"] == Decimal("74")
    assert spec["powertrain"]["displacement_cc"] == 999


def test_advisor_reads_the_same_v2_dimensions_and_power_as_the_detail(db, tmp_path):
    publish_dimensioned(db, tmp_path)
    candidates = AdvisorRepository(db).list_candidates()
    ice = next(c for c in candidates if c["spec"]["variant_key"] == "metro-g1-ice")
    context = ice["decision_context"]
    assert context["dimensions"]["length_mm"] == 4010
    assert context["dimensions"]["body_width_mm"] == 1750
    assert context["dimensions"]["height_mm"] is None
    assert context["powertrain"]["power_kw"] == Decimal("74")
    credited = {item["metric"] for item in ice["provenance"] if "metric" in item}
    assert {"length_mm", "width_mm", "power_kw"} <= credited


def test_listing_and_resolve_candidates_keep_consumption_basis(db, tmp_path):
    data = permitted_bundle(tmp_path)
    add_interval(data, "liquid_consumption_l_100km", 4.4, 4.9, wltp())
    publish(db, data, tmp_path)
    spec = db.execute(
        "SELECT * FROM vehicle_specs WHERE variant_key = 'metro-g1-ice'"
    ).fetchone()
    source_id = db.execute(
        "SELECT id FROM sources WHERE source_key = 'synthetic-v2'"
    ).fetchone()["id"]
    listing_id = uuid4()
    db.execute(
        """INSERT INTO listings (id, vehicle_id, spec_id, source_id, listing_ref, title,
               price_eur, mileage, condition, source_url, first_seen_at, last_seen_at,
               content_hash)
           VALUES (%s, %s, %s, %s, 'basis', 'Basis offer', 10000, 1000, 'used',
               'https://example.test/offer', now(), now(), 'basis')""",
        (listing_id, spec["vehicle_id"], spec["id"], source_id),
    )
    listing = ListingWithVehicle.model_validate(
        ListingsRepository(db).get_listing(listing_id)
    )
    assert listing.spec.consumption_l_100km_basis == "interval_upper"
    listed = ListingsRepository(db).list_listings(ListingFilters(spec_id=spec["id"]))
    assert listed[0]["spec"]["consumption_l_100km_basis"] == "interval_upper"
    resolve = [
        row
        for row in VehiclesRepository(db).list_resolve_candidates("IT")
        if row["spec_id"] == spec["id"]
    ]
    assert resolve[0]["consumption_l_100km_basis"] == "interval_upper"
    assert "energy_consumption_kwh_100km_basis" in resolve[0]


def test_vehicle_exists(db, tmp_path):
    publish(db, permitted_bundle(tmp_path), tmp_path)
    repo = VehiclesRepository(db)
    assert repo.vehicle_exists(vehicle_id(db, "metro-g1-2026")) is True
    assert repo.vehicle_exists(uuid4()) is False


def test_user_wildcards_match_literally(db, tmp_path):
    publish(db, permitted_bundle(tmp_path), tmp_path)
    repo = VehiclesRepository(db)
    assert repo.list_vehicles(VehicleFilters(make="Acme"))
    # Unescaped, "_" and "%" would match any character: "_cme" would find Acme.
    assert repo.list_vehicles(VehicleFilters(make="_cme")) == []
    assert repo.list_vehicles(VehicleFilters(make="%")) == []
    assert repo.list_vehicles(VehicleFilters(model="\\")) == []


class RecordingConnection:
    def __init__(self) -> None:
        self.query = ""
        self.params: list[object] = []

    def execute(self, query, params=None):
        self.query, self.params = query, params
        return self

    def fetchall(self):
        return []

    def __iter__(self):
        return iter([])


def test_contains_pattern_escapes_like_wildcards():
    assert contains_pattern("ab") == "%ab%"
    assert contains_pattern("50%_off\\x") == "%50\\%\\_off\\\\x%"


def test_repositories_escape_every_user_pattern():
    vehicles = RecordingConnection()
    VehiclesRepository(vehicles).list_vehicles(VehicleFilters(make="a_b", model="c%"))
    assert "v.make ILIKE %s ESCAPE '\\'" in vehicles.query
    assert "v.model ILIKE %s ESCAPE '\\'" in vehicles.query
    assert vehicles.params[:2] == ["%a\\_b%", "%c\\%%"]

    listings = RecordingConnection()
    ListingsRepository(listings).list_listings(
        ListingFilters(make="a_b", model="c%", location_region="x_y")
    )
    for column in ("v.make", "v.model", "l.location_region"):
        assert f"{column} ILIKE %s ESCAPE '\\'" in listings.query
    assert listings.params[:3] == ["%a\\_b%", "%c\\%%", "%x\\_y%"]

    documents = RecordingConnection()
    DocumentsRepository(documents).list_documents(DocumentFilters(q="10%"))
    assert documents.query.count("ESCAPE '\\'") == 2
    assert documents.params[:2] == ["%10\\%%", "%10\\%%"]

    search = RecordingConnection()
    DocumentsRepository(search).search_document_candidates(
        query="a_b", tokens=("a_b",), document_type=None, limit=5
    )
    assert search.query.count("ESCAPE '\\'") == 4
    assert search.params == ["%a\\_b%"] * 4 + [5]


def test_migration_runner_takes_the_lock_before_reading_the_ledger(monkeypatch):
    statements: list[str] = []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=None):
            statements.append(query.strip())
            return self

        def fetchall(self):
            return []

    monkeypatch.setattr(migrations, "load_migrations", lambda: [])
    monkeypatch.setattr(migrations.psycopg, "connect", lambda _url: FakeConnection())
    migrations.run_migrations("postgresql://unused")
    assert statements[0] == "SELECT pg_advisory_xact_lock(%s)"
    assert statements[1].startswith("CREATE TABLE IF NOT EXISTS drivewise_schema_migrations")


def test_concurrent_runner_waits_for_the_migration_lock():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    run_migrations(url)
    result: dict[str, object] = {}

    def second_runner():
        result["run"] = run_migrations(url)

    with psycopg.connect(url) as holder:
        holder.execute("SELECT pg_advisory_xact_lock(%s)", (migrations.MIGRATION_LOCK_KEY,))
        runner = threading.Thread(target=second_runner)
        runner.start()
        deadline = time.monotonic() + 10
        waiting = 0
        with psycopg.connect(url, autocommit=True) as observer:
            while time.monotonic() < deadline and not waiting:
                waiting = observer.execute(
                    "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory'"
                    " AND NOT granted AND objid = %s",
                    (migrations.MIGRATION_LOCK_KEY & 0xFFFFFFFF,),
                ).fetchone()[0]
                time.sleep(0.05)
        assert waiting == 1
        assert runner.is_alive()
        holder.rollback()
    runner.join(timeout=30)
    assert not runner.is_alive()
    assert result["run"].applied == []
