import os
import re
from uuid import UUID, uuid4

import pytest
from psycopg import sql
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
    "import_runs",
    "vehicle_provenance",
    "vehicle_spec_provenance",
    "vehicle_maintenance_items",
    "vehicle_safety_ratings",
    "vehicle_features",
    "vehicle_media_assets",
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
        "0004_curated_catalog.sql",
        "0005_vehicle_knowledge_profile.sql",
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


def test_curated_catalog_migration_preserves_legacy_rows_conservatively():
    sql = (MIGRATIONS_PATH / "0004_curated_catalog.sql").read_text()

    assert "canonical_key text" in sql
    assert "model_family_key text" in sql
    assert "variant_key text" in sql
    assert "DROP CONSTRAINT IF EXISTS vehicle_specs_vehicle_id_trim_key" in sql
    assert "vehicle_specs_one_default_per_vehicle_idx" in sql
    assert "vehicle_specs_id_vehicle_id_key UNIQUE (id, vehicle_id)" in sql
    assert "listings_spec_vehicle_match_fkey" in sql
    assert "FOREIGN KEY (spec_id, vehicle_id)" in sql
    assert "ranking_permission text NOT NULL" in sql
    assert "sources_ranking_permission_check" in sql
    assert "record_observed_at timestamptz NOT NULL" in sql
    assert "is_current boolean NOT NULL DEFAULT true" in sql
    assert "HAVING count(*) = 1" in sql
    assert "listing.spec_id IS NULL" in sql
    assert "CREATE TABLE IF NOT EXISTS import_runs" in sql
    assert "CREATE TABLE IF NOT EXISTS vehicle_provenance" in sql
    assert "CREATE TABLE IF NOT EXISTS vehicle_spec_provenance" in sql
    assert "score_breakdown jsonb" in sql
    assert "condition_group text NOT NULL DEFAULT 'legacy'" in sql
    assert "DROP CONSTRAINT IF EXISTS recommendation_items_run_id_vehicle_id_key" in sql
    assert "recommendation_items_run_group_vehicle_key" in sql
    assert "DROP CONSTRAINT IF EXISTS recommendation_items_run_id_rank_key" in sql
    assert "recommendation_items_run_group_rank_key" in sql
    assert "recommendation_items_listing_identity_fkey" in sql
    assert "assumptions jsonb" in sql
    assert "exclusion_counts jsonb" in sql


def test_vehicle_knowledge_profile_migration_is_relational_and_constrained():
    sql = (MIGRATIONS_PATH / "0005_vehicle_knowledge_profile.sql").read_text()

    for column in [
        "generation_name text",
        "engine_code text",
        "length_mm integer",
        "power_kw numeric(7, 2)",
        "acceleration_0_100_s numeric(5, 2)",
        "homologation_cycle text",
    ]:
        assert column in sql

    for table in [
        "vehicle_maintenance_items",
        "vehicle_safety_ratings",
        "vehicle_features",
        "vehicle_media_assets",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql

    assert "vehicle_maintenance_interval_check" in sql
    assert "vehicle_features_category_check" in sql
    assert "vehicle_features_availability_check" in sql
    assert "vehicle_media_assets_type_check" in sql
    assert "vehicle_media_assets_https_check" in sql
    assert sql.count("source_url LIKE 'https://%'") == 4
    assert "ON DELETE CASCADE" in sql


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not configured",
)
def test_curated_catalog_migration_preserves_ids_and_leaves_ambiguous_listing_unlinked():
    import psycopg

    database_url = os.environ["TEST_DATABASE_URL"]
    schema_name = f"catalog_migration_{uuid4().hex}"

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        conn.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name))
        )
        try:
            conn.execute(
                sql.SQL("SET search_path TO {}, public").format(
                    sql.Identifier(schema_name)
                )
            )
            conn.execute(
                (MIGRATIONS_PATH / "0002_create_mvp_schema.sql").read_text()
            )
            conn.execute(
                (MIGRATIONS_PATH / "0003_seed_initial_vehicles.sql").read_text()
            )
            conn.execute(
                """
                INSERT INTO vehicle_specs (
                  id, vehicle_id, trim, seats, cargo_volume_liters
                )
                VALUES (
                  '20000000-0000-4000-8000-000000000099',
                  '00000000-0000-4000-8000-000000000001',
                  'Ambiguous second variant',
                  4,
                  225
                )
                """
            )
            ids_before = {
                "vehicles": [
                    row["id"]
                    for row in conn.execute(
                        "SELECT id FROM vehicles ORDER BY id"
                    ).fetchall()
                ],
                "specs": [
                    row["id"]
                    for row in conn.execute(
                        "SELECT id FROM vehicle_specs ORDER BY id"
                    ).fetchall()
                ],
                "listings": [
                    row["id"]
                    for row in conn.execute(
                        "SELECT id FROM listings ORDER BY id"
                    ).fetchall()
                ],
            }

            conn.execute(
                (MIGRATIONS_PATH / "0004_curated_catalog.sql").read_text()
            )

            ids_after = {
                "vehicles": [
                    row["id"]
                    for row in conn.execute(
                        "SELECT id FROM vehicles ORDER BY id"
                    ).fetchall()
                ],
                "specs": [
                    row["id"]
                    for row in conn.execute(
                        "SELECT id FROM vehicle_specs ORDER BY id"
                    ).fetchall()
                ],
                "listings": [
                    row["id"]
                    for row in conn.execute(
                        "SELECT id FROM listings ORDER BY id"
                    ).fetchall()
                ],
            }
            fiat_listing = conn.execute(
                """
                SELECT spec_id
                FROM listings
                WHERE id = '30000000-0000-4000-8000-000000000001'
                """
            ).fetchone()
            linked_unambiguous = conn.execute(
                """
                SELECT count(*) AS count
                FROM listings
                WHERE id <> '30000000-0000-4000-8000-000000000001'
                  AND spec_id IS NOT NULL
                """
            ).fetchone()
            fiat_variants = conn.execute(
                """
                SELECT variant_key, is_default
                FROM vehicle_specs
                WHERE vehicle_id = '00000000-0000-4000-8000-000000000001'
                ORDER BY variant_key
                """
            ).fetchall()

            assert ids_after == ids_before
            assert fiat_listing == {"spec_id": None}
            assert linked_unambiguous == {"count": 4}
            assert len({row["variant_key"] for row in fiat_variants}) == 2
            assert sum(row["is_default"] for row in fiat_variants) == 1

            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                with conn.transaction():
                    conn.execute(
                        """
                        UPDATE listings
                        SET spec_id = '20000000-0000-4000-8000-000000000002'
                        WHERE id = '30000000-0000-4000-8000-000000000001'
                        """
                    )
        finally:
            conn.execute("SET search_path TO public")
            conn.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(
                    sql.Identifier(schema_name)
                )
            )


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
        linked_listing_count = conn.execute(
            "SELECT count(*) FROM listings WHERE spec_id IS NOT NULL"
        ).fetchone()
        default_spec_count = conn.execute(
            "SELECT count(*) FROM vehicle_specs WHERE is_default"
        ).fetchone()
        seed_source_permission = conn.execute(
            """
            SELECT ranking_permission
            FROM sources
            WHERE id = '10000000-0000-4000-8000-000000000001'
            """
        ).fetchone()
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with conn.transaction():
                conn.execute(
                    """
                    UPDATE listings
                    SET spec_id = '20000000-0000-4000-8000-000000000002'
                    WHERE id = '30000000-0000-4000-8000-000000000001'
                    """
                )
        fiat_listing_spec = conn.execute(
            """
            SELECT spec_id
            FROM listings
            WHERE id = '30000000-0000-4000-8000-000000000001'
            """
        ).fetchone()

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
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO recommendation_items (
                      id, run_id, vehicle_id, listing_id, spec_id, rank
                    )
                    VALUES (
                      '50000000-0000-4000-8000-000000000099',
                      %s,
                      '00000000-0000-4000-8000-000000000002',
                      '30000000-0000-4000-8000-000000000001',
                      '20000000-0000-4000-8000-000000000002',
                      99
                    )
                    """,
                    (run_id,),
                )

        extra_spec_id = "20000000-0000-4000-8000-000000000099"
        conn.execute(
            """
            INSERT INTO vehicle_specs (
              id, vehicle_id, variant_key, is_default, trim, body_style,
              fuel_type, list_price_eur, energy_consumption_kwh_100km,
              wltp_range_km, seats, cargo_volume_liters
            )
            VALUES (
              %s, '00000000-0000-4000-8000-000000000001',
              'it-fiat-panda-2024-city-electric-test', false,
              '1.0 FireFly Hybrid', 'city_car', 'electric', 14900,
              15.5, 300, 4, 225
            )
            """,
            (extra_spec_id,),
        )
        non_default_match = VehiclesRepository(conn).list_vehicles(
            VehicleFilters(
                fuel_type="electric",
                body_style="city_car",
                market="IT",
                max_price_eur=15000,
                limit=10,
            )
        )
        conn.execute("DELETE FROM vehicle_specs WHERE id = %s", (extra_spec_id,))

    assert extension_name == {"extname": "vector"}
    assert vehicle_count == {"count": 5}
    assert document_count == {"count": 5}
    assert linked_listing_count == {"count": 5}
    assert default_spec_count == {"count": 5}
    assert seed_source_permission == {"ranking_permission": "not_permitted"}
    assert fiat_listing_spec == {
        "spec_id": UUID("20000000-0000-4000-8000-000000000001")
    }
    assert [vehicle["make"] for vehicle in vehicles] == ["Dacia"]
    assert [listing["location_region"] for listing in listings] == ["Lazio"]
    assert any(
        document["title"] == "Synthetic profile: Fiat Panda"
        for document in documents
    )
    assert saved_items["count"] == len(items)
    assert [vehicle["make"] for vehicle in non_default_match] == ["Fiat"]
    assert non_default_match[0]["fuel_type"] == "mild_hybrid_petrol"
