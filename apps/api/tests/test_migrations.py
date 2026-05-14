import os
import re

import pytest
from psycopg.rows import dict_row

from app.repositories.advisor import AdvisorRepository
from app.repositories.documents import DocumentsRepository
from app.repositories.filters import DocumentFilters, ListingFilters, VehicleFilters
from app.repositories.listings import ListingsRepository
from app.repositories.vehicles import VehiclesRepository
from app.schemas.advisor import AdvisorRecommendationRequest
from app.services.advisor.scoring import build_recommendations
from app.db.migrations import MIGRATIONS_PATH, apply_migrations, iter_migration_files


REQUIRED_TABLES = {
    "vehicles",
    "vehicle_specs",
    "sources",
    "listings",
    "documents",
    "recommendation_runs",
    "recommendation_items",
}


def read_migration_sql() -> str:
    return "\n".join(path.read_text() for path in iter_migration_files())


def test_migration_files_are_ordered():
    names = [path.name for path in iter_migration_files()]

    assert names == sorted(names)
    assert names == [
        "0001_enable_pgvector.sql",
        "0002_create_mvp_schema.sql",
        "0003_seed_initial_vehicles.sql",
    ]


def test_schema_creates_pgvector_and_required_tables():
    sql = read_migration_sql()

    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert "embedding vector(1536)" in sql
    assert "base_price_eur numeric(12, 2)" in sql
    assert "price_eur numeric(12, 2)" in sql
    assert "consumption_l_100km numeric(5, 2)" in sql
    assert "wltp_range_km integer" in sql
    assert "co2_g_km integer" in sql
    assert "euro_emission_standard text" in sql
    assert "cargo_volume_liters numeric(7, 2)" in sql
    assert "base_msrp_usd" not in sql
    assert "price_usd" not in sql
    assert "cargo_volume_cuft" not in sql
    assert "epa_city_mpg" not in sql
    assert "epa_highway_mpg" not in sql
    assert "epa_combined_mpg" not in sql
    assert "epa_range_miles" not in sql

    for table_name in REQUIRED_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in sql


def test_seed_contains_five_synthetic_vehicles():
    seed_sql = (MIGRATIONS_PATH / "0003_seed_initial_vehicles.sql").read_text()
    vehicle_values = re.search(
        r"INSERT INTO vehicles .*?VALUES\s*(?P<values>.*?)\s*ON CONFLICT",
        seed_sql,
        flags=re.DOTALL,
    )

    assert vehicle_values is not None
    assert vehicle_values.group("values").count("00000000-0000-4000-8000-") == 5
    assert "'IT'" in vehicle_values.group("values")
    assert "'US'" not in vehicle_values.group("values")
    assert "Synthetic seed data" in seed_sql

    for vehicle_name in [
        "Fiat",
        "Panda",
        "Toyota",
        "Yaris Hybrid",
        "Volkswagen",
        "Golf",
        "Dacia",
        "Sandero",
        "Tesla",
        "Model 3",
    ]:
        assert vehicle_name in seed_sql


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not configured",
)
def test_migrations_apply_to_configured_test_database():
    import psycopg

    database_url = os.environ["TEST_DATABASE_URL"]

    apply_migrations(database_url)

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        extension_name = conn.execute(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        vehicle_count = conn.execute("SELECT count(*) FROM vehicles").fetchone()
        document_count = conn.execute("SELECT count(*) FROM documents").fetchone()

        vehicles = VehiclesRepository(conn).list_vehicles(
            VehicleFilters(make="dac", limit=10)
        )
        listings = ListingsRepository(conn).list_listings(
            ListingFilters(location_region="zio", limit=10)
        )
        documents = DocumentsRepository(conn).list_documents(
            DocumentFilters(q="compact", limit=10)
        )

        advisor_repository = AdvisorRepository(conn)
        request = AdvisorRecommendationRequest(
            budget_max_eur=15000,
            primary_use="city",
            priorities=["price"],
        )
        items = build_recommendations(request, advisor_repository.list_candidates())
        run_id = advisor_repository.create_run(request.model_dump(mode="json"))
        advisor_repository.save_items(run_id, items)
        advisor_repository.mark_run_completed(run_id)
        saved_items = conn.execute(
            "SELECT count(*) AS count FROM recommendation_items WHERE run_id = %s",
            (run_id,),
        ).fetchone()

    assert extension_name == {"extname": "vector"}
    assert vehicle_count == {"count": 5}
    assert document_count == {"count": 5}
    assert [vehicle["make"] for vehicle in vehicles] == ["Dacia"]
    assert [listing["location_region"] for listing in listings] == ["Lazio"]
    assert any(
        document["title"] == "Synthetic profile: Fiat Panda"
        for document in documents
    )
    assert saved_items["count"] == len(items)
