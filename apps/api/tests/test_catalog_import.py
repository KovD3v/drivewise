import importlib.util
import json
import os
from datetime import datetime
from pathlib import Path

import pytest
from psycopg.rows import dict_row

from app.db.migrations import apply_migrations
from app.ingestion.catalog import (
    CatalogValidationError,
    ProvenanceClaim,
    compute_catalog_hash,
    import_catalog,
    load_catalog,
    validate_catalog,
)
from app.repositories.vehicles import VehiclesRepository


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "data/fixtures/catalog/catalog-v1.synthetic.json"
SCRIPT_PATH = ROOT / "apps/api/scripts/import_catalog.py"


def load_import_script():
    spec = importlib.util.spec_from_file_location(
        "drivewise_import_catalog_script", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_fixture_validates_cross_references_and_same_trim_variants():
    payload = load_catalog(FIXTURE_PATH)

    summary = validate_catalog(payload)

    assert summary.vehicles == len(payload.vehicles)
    assert summary.variants == len(payload.variants)
    assert payload.variants[0].trim == payload.variants[1].trim
    assert payload.variants[0].variant_key != payload.variants[1].variant_key
    assert len(compute_catalog_hash(payload)) == 64


def test_catalog_loads_complete_vehicle_profile_fixture():
    payload = load_catalog(FIXTURE_PATH)
    variant = next(
        item
        for item in payload.variants
        if item.variant_key == "it-acme-metro-2026-petrol"
    )

    assert variant.engine_code == "SYN-T10"
    assert variant.power_kw == 74
    assert len(variant.maintenance_schedule) == 2
    assert len(variant.safety_ratings) == 1
    assert {item.category for item in variant.features} == {
        "adas",
        "safety",
        "technology",
        "comfort",
    }
    assert {item.asset_type for item in variant.media} == {
        "photo",
        "brochure",
        "manual",
    }


def test_catalog_json_schema_accepts_enriched_fixture():
    from jsonschema import Draft202012Validator, FormatChecker

    schema_path = ROOT / "docs/catalog-v1.schema.json"
    schema = json.loads(schema_path.read_text())
    instance = json.loads(FIXTURE_PATH.read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(instance)


def test_catalog_distinguishes_omitted_and_explicitly_empty_profile_collections():
    payload = load_catalog(FIXTURE_PATH)
    enriched = payload.variants[0]
    unenriched = payload.variants[1]

    assert "maintenance_schedule" in enriched.model_fields_set
    assert "maintenance_schedule" not in unenriched.model_fields_set
    cleared = unenriched.model_copy(update={"maintenance_schedule": []})
    cleared.__pydantic_fields_set__.add("maintenance_schedule")
    assert "maintenance_schedule" in cleared.model_fields_set


def test_catalog_vehicle_profile_rejects_maintenance_without_an_interval(tmp_path):
    raw_payload = json.loads(FIXTURE_PATH.read_text())
    raw_payload["variants"][0]["maintenance_schedule"] = [
        {
            "operation_code": "engine-oil",
            "title": "Engine oil and filter",
            "source_key": "drivewise-synthetic-catalog",
            "source_url": "https://example.test/maintenance/engine-oil",
            "observed_at": "2026-07-16T09:00:00+02:00",
        }
    ]
    path = tmp_path / "invalid-maintenance.json"
    path.write_text(json.dumps(raw_payload))

    with pytest.raises(CatalogValidationError, match="requires an interval"):
        load_catalog(path)


def test_catalog_vehicle_profile_rejects_unknown_child_source(tmp_path):
    raw_payload = json.loads(FIXTURE_PATH.read_text())
    raw_payload["variants"][0]["features"] = [
        {
            "feature_key": "adaptive-cruise-control",
            "category": "adas",
            "name": "Adaptive cruise control",
            "availability": "standard",
            "source_key": "missing-source",
            "source_url": "https://example.test/features/adaptive-cruise-control",
            "observed_at": "2026-07-16T09:00:00+02:00",
        }
    ]
    path = tmp_path / "unknown-child-source.json"
    path.write_text(json.dumps(raw_payload))

    with pytest.raises(CatalogValidationError, match="feature_key references unknown"):
        load_catalog(path)


@pytest.mark.parametrize(
    ("collection", "record", "duplicate_message"),
    [
        (
            "maintenance_schedule",
            {
                "operation_code": "engine-oil",
                "title": "Engine oil and filter",
                "interval_km": 15000,
            },
            "duplicate it-acme-metro-2026-petrol maintenance operation_code",
        ),
        (
            "safety_ratings",
            {
                "assessment_system": "Euro NCAP",
                "assessment_year": 2026,
            },
            "duplicate it-acme-metro-2026-petrol safety assessment",
        ),
        (
            "features",
            {
                "feature_key": "adaptive-cruise-control",
                "category": "adas",
                "name": "Adaptive cruise control",
                "availability": "standard",
            },
            "duplicate it-acme-metro-2026-petrol feature_key",
        ),
        (
            "media",
            {
                "asset_key": "metro-exterior",
                "asset_type": "photo",
                "title": "Metro exterior",
                "url": "https://example.test/media/metro-exterior.jpg",
            },
            "duplicate it-acme-metro-2026-petrol media asset_key",
        ),
    ],
)
def test_catalog_vehicle_profile_rejects_duplicate_child_keys(
    collection,
    record,
    duplicate_message,
    tmp_path,
):
    raw_payload = json.loads(FIXTURE_PATH.read_text())
    child_source = {
        "source_key": "drivewise-synthetic-catalog",
        "source_url": "https://example.test/catalog/metro",
        "observed_at": "2026-07-16T09:00:00+02:00",
    }
    raw_payload["variants"][0][collection] = [
        {**record, **child_source},
        {**record, **child_source},
    ]
    path = tmp_path / f"duplicate-{collection}.json"
    path.write_text(json.dumps(raw_payload))

    with pytest.raises(CatalogValidationError, match=duplicate_message):
        load_catalog(path)


def test_catalog_vehicle_profile_rejects_http_media_url(tmp_path):
    raw_payload = json.loads(FIXTURE_PATH.read_text())
    raw_payload["variants"][0]["media"] = [
        {
            "asset_key": "metro-exterior",
            "asset_type": "photo",
            "title": "Metro exterior",
            "url": "http://example.test/media/metro-exterior.jpg",
            "source_key": "drivewise-synthetic-catalog",
            "source_url": "https://example.test/catalog/metro",
            "observed_at": "2026-07-16T09:00:00+02:00",
        }
    ]
    path = tmp_path / "http-media.json"
    path.write_text(json.dumps(raw_payload))

    with pytest.raises(CatalogValidationError, match="media URL must use https"):
        load_catalog(path)


def test_catalog_vehicle_profile_rejects_malformed_https_media_url(tmp_path):
    raw_payload = json.loads(FIXTURE_PATH.read_text())
    raw_payload["variants"][0]["media"] = [
        {
            "asset_key": "metro-exterior",
            "asset_type": "photo",
            "title": "Metro exterior",
            "url": "https://",
            "source_key": "drivewise-synthetic-catalog",
            "source_url": "https://example.test/catalog/metro",
            "observed_at": "2026-07-16T09:00:00+02:00",
        }
    ]
    path = tmp_path / "malformed-https-media.json"
    path.write_text(json.dumps(raw_payload))

    with pytest.raises(CatalogValidationError, match="absolute http\\(s\\) URL"):
        load_catalog(path)


def test_catalog_vehicle_profile_rejects_zero_payload_kg(tmp_path):
    raw_payload = json.loads(FIXTURE_PATH.read_text())
    raw_payload["variants"][0]["payload_kg"] = 0
    path = tmp_path / "zero-payload.json"
    path.write_text(json.dumps(raw_payload))

    with pytest.raises(CatalogValidationError, match="payload_kg"):
        load_catalog(path)


def test_catalog_requires_exactly_one_default_variant():
    payload = load_catalog(FIXTURE_PATH).model_copy(deep=True)
    payload.variants[1].is_default = True

    with pytest.raises(CatalogValidationError, match="exactly one default variant"):
        validate_catalog(payload)


def test_catalog_rejects_unknown_listing_variant_before_database_work():
    payload = load_catalog(FIXTURE_PATH).model_copy(deep=True)
    payload.listings[0].variant_key = "missing-variant"

    with pytest.raises(CatalogValidationError, match="unknown variant_key"):
        validate_catalog(payload)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [("fuel_type", "steam"), ("body_style", "hovercraft")],
)
def test_catalog_rejects_unknown_scoring_enums(
    field,
    invalid_value,
    tmp_path,
):
    raw_payload = json.loads(FIXTURE_PATH.read_text())
    raw_payload["variants"][0][field] = invalid_value
    invalid_path = tmp_path / "invalid-catalog.json"
    invalid_path.write_text(json.dumps(raw_payload))

    with pytest.raises(CatalogValidationError, match=field):
        load_catalog(invalid_path)


@pytest.mark.parametrize("invalid_value", [None, "manual_only", ""])
def test_catalog_requires_explicit_valid_ranking_permission(
    invalid_value,
    tmp_path,
):
    raw_payload = json.loads(FIXTURE_PATH.read_text())
    if invalid_value is None:
        del raw_payload["sources"][0]["ranking_permission"]
    else:
        raw_payload["sources"][0]["ranking_permission"] = invalid_value
    invalid_path = tmp_path / "invalid-source-permission.json"
    invalid_path.write_text(json.dumps(raw_payload))

    with pytest.raises(CatalogValidationError, match="ranking_permission"):
        load_catalog(invalid_path)


def test_catalog_check_mode_needs_no_database_url(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    module = load_import_script()

    exit_code = module.main(
        ["--path", str(FIXTURE_PATH), "--check"],
        env_path=tmp_path / ".env",
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Catalog is valid." in captured.out
    expected_variants = len(load_catalog(FIXTURE_PATH).variants)
    assert f"Variants: {expected_variants}" in captured.out


def test_catalog_cli_requires_exactly_one_mode():
    module = load_import_script()

    with pytest.raises(SystemExit):
        module.parse_args(["--path", str(FIXTURE_PATH)])
    with pytest.raises(SystemExit):
        module.parse_args(
            ["--path", str(FIXTURE_PATH), "--check", "--write"]
        )


def test_catalog_cli_reports_write_validation_error_without_traceback(
    monkeypatch,
    capsys,
    tmp_path,
):
    module = load_import_script()

    class ConnectionContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:test@localhost:5432/drivewise",
    )
    monkeypatch.setattr(module, "load_env_file", lambda _path: None)
    monkeypatch.setattr(
        module.psycopg,
        "connect",
        lambda *_args, **_kwargs: ConnectionContext(),
    )
    monkeypatch.setattr(
        module,
        "import_catalog",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CatalogValidationError("listing stale-offer is older than stored data")
        ),
    )

    exit_code = module.main(
        ["--path", str(FIXTURE_PATH), "--write"],
        env_path=tmp_path / ".env",
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == (
        "Catalog import rejected: listing stale-offer is older than stored data\n"
    )
    assert "Traceback" not in captured.err


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not configured",
)
def test_catalog_write_is_idempotent_updates_and_rolls_back_atomically():
    import psycopg

    database_url = os.environ["TEST_DATABASE_URL"]
    apply_migrations(database_url)

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
        autocommit=True,
    ) as conn:
        _cleanup_catalog_test_rows(conn)
        try:
            payload = load_catalog(FIXTURE_PATH).model_copy(deep=True)
            payload.vehicles = payload.vehicles[:1]
            payload.variants = payload.variants[:2]
            payload.listings = payload.listings[:2]
            first = import_catalog(conn, payload, file_name="pytest-catalog-base.json")
            profile = conn.execute(
                """
                SELECT
                  spec.engine_code,
                  (
                    SELECT count(*)
                    FROM vehicle_maintenance_items item
                    WHERE item.spec_id = spec.id
                  ) AS maintenance_count,
                  (
                    SELECT count(*)
                    FROM vehicle_safety_ratings rating
                    WHERE rating.spec_id = spec.id
                  ) AS safety_rating_count,
                  (
                    SELECT count(*)
                    FROM vehicle_features feature
                    WHERE feature.spec_id = spec.id
                  ) AS feature_count,
                  (
                    SELECT count(*)
                    FROM vehicle_media_assets asset
                    WHERE asset.spec_id = spec.id
                  ) AS media_count
                FROM vehicle_specs spec
                WHERE spec.variant_key = 'it-acme-metro-2026-petrol'
                """
            ).fetchone()
            listing_before = conn.execute(
                """
                SELECT id, price_eur, is_active
                FROM listings
                WHERE listing_ref = 'synthetic-acme-metro-petrol-new'
                """
            ).fetchone()
            same = import_catalog(conn, payload, file_name="pytest-catalog-base.json")

            assert first.status == "completed"
            assert first.counts.inserted == 5
            assert profile == {
                "engine_code": "SYN-T10",
                "maintenance_count": 2,
                "safety_rating_count": 1,
                "feature_count": 4,
                "media_count": 3,
            }
            assert same.status == "unchanged"
            assert same.run_id == first.run_id
            assert conn.execute(
                """
                SELECT count(*) AS count
                FROM vehicles
                WHERE canonical_key = 'it-acme-metro-2026'
                """
            ).fetchone() == {"count": 1}
            assert conn.execute(
                """
                SELECT count(*) AS count
                FROM vehicle_specs
                WHERE vehicle_id = (
                  SELECT id FROM vehicles WHERE canonical_key = 'it-acme-metro-2026'
                ) AND trim = 'City'
                """
            ).fetchone() == {"count": 2}
            assert conn.execute(
                """
                SELECT ranking_permission
                FROM sources
                WHERE source_key = 'drivewise-synthetic-catalog'
                """
            ).fetchone() == {"ranking_permission": "permitted"}
            imported_vehicle_id = conn.execute(
                """
                SELECT id FROM vehicles
                WHERE canonical_key = 'it-acme-metro-2026'
                """
            ).fetchone()["id"]
            vehicle_detail = VehiclesRepository(conn).get_vehicle(imported_vehicle_id)
            assert vehicle_detail is not None
            assert vehicle_detail["provenance"][0]["source_key"] == (
                "drivewise-synthetic-catalog"
            )
            assert all(spec["provenance"] for spec in vehicle_detail["specs"])
            petrol_provenance = vehicle_detail["specs"][0]["provenance"][0]
            assert "body_style" in petrol_provenance["supported_metrics"]
            assert "consumption_l_100km" in petrol_provenance["supported_metrics"]
            assert "battery_kwh" not in petrol_provenance["supported_metrics"]

            omitted_maintenance = payload.model_copy(deep=True)
            omitted_maintenance.variants[0].list_price_eur = 16850
            omitted_maintenance.variants[0].maintenance_schedule = []
            omitted_maintenance.variants[0].__pydantic_fields_set__.discard(
                "maintenance_schedule"
            )
            import_catalog(
                conn,
                omitted_maintenance,
                file_name="pytest-catalog-omitted-maintenance.json",
            )
            assert conn.execute(
                """
                SELECT count(*) AS count
                FROM vehicle_maintenance_items item
                JOIN vehicle_specs spec ON spec.id = item.spec_id
                WHERE spec.variant_key = 'it-acme-metro-2026-petrol'
                """
            ).fetchone() == {"count": 2}

            cleared_maintenance = omitted_maintenance.model_copy(deep=True)
            cleared_maintenance.variants[0].list_price_eur = 16875
            cleared_maintenance.variants[0].__pydantic_fields_set__.add(
                "maintenance_schedule"
            )
            import_catalog(
                conn,
                cleared_maintenance,
                file_name="pytest-catalog-cleared-maintenance.json",
            )
            assert conn.execute(
                """
                SELECT count(*) AS count
                FROM vehicle_maintenance_items item
                JOIN vehicle_specs spec ON spec.id = item.spec_id
                WHERE spec.variant_key = 'it-acme-metro-2026-petrol'
                """
            ).fetchone() == {"count": 0}
            same_cleared = import_catalog(
                conn,
                cleared_maintenance,
                file_name="pytest-catalog-cleared-maintenance.json",
            )
            assert same_cleared.status == "unchanged"
            assert conn.execute(
                """
                SELECT count(*) AS count
                FROM vehicle_maintenance_items item
                JOIN vehicle_specs spec ON spec.id = item.spec_id
                WHERE spec.variant_key = 'it-acme-metro-2026-petrol'
                """
            ).fetchone() == {"count": 0}

            changed = payload.model_copy(deep=True)
            changed.listings[0].price_eur = 16950
            updated = import_catalog(
                conn,
                changed,
                file_name="pytest-catalog-price-update.json",
            )
            listing_after = conn.execute(
                """
                SELECT id, price_eur, is_active
                FROM listings
                WHERE listing_ref = 'synthetic-acme-metro-petrol-new'
                """
            ).fetchone()

            assert updated.status == "completed"
            assert updated.counts.updated >= 1
            assert listing_after["id"] == listing_before["id"]
            assert float(listing_after["price_eur"]) == 16950

            omitted = changed.model_copy(deep=True)
            omitted.listings = omitted.listings[:1]
            import_catalog(
                conn,
                omitted,
                file_name="pytest-catalog-omitted-listing.json",
            )
            still_active = conn.execute(
                """
                SELECT is_active
                FROM listings
                WHERE listing_ref = 'synthetic-acme-metro-electric-new'
                """
            ).fetchone()
            assert still_active == {"is_active": True}

            deactivated = changed.model_copy(deep=True)
            deactivated.listings[1].is_active = False
            result = import_catalog(
                conn,
                deactivated,
                file_name="pytest-catalog-deactivate.json",
            )
            inactive = conn.execute(
                """
                SELECT is_active
                FROM listings
                WHERE listing_ref = 'synthetic-acme-metro-electric-new'
                """
            ).fetchone()
            assert result.counts.deactivated == 1
            assert inactive == {"is_active": False}

            failing = payload.model_copy(deep=True)
            failing.vehicles[0].canonical_key = "it-acme-overflow-2026"
            failing.vehicles[0].model_family_key = "it-acme-overflow"
            failing.vehicles[0].model = "Overflow"
            failing.variants = failing.variants[:1]
            failing.variants[0].vehicle_key = "it-acme-overflow-2026"
            failing.variants[0].variant_key = "it-acme-overflow-2026-default"
            failing.variants[0].list_price_eur = 1e20
            failing.listings = []
            failing_hash = compute_catalog_hash(failing)

            with pytest.raises(psycopg.Error):
                import_catalog(
                    conn,
                    failing,
                    file_name="pytest-catalog-failure.json",
                )

            assert conn.execute(
                """
                SELECT count(*) AS count
                FROM vehicles
                WHERE canonical_key = 'it-acme-overflow-2026'
                """
            ).fetchone() == {"count": 0}
            failed_run = conn.execute(
                """
                SELECT status, error_message
                FROM import_runs
                WHERE dataset_hash = %s
                """,
                (failing_hash,),
            ).fetchone()
            assert failed_run["status"] == "failed"
            assert "NumericValueOutOfRange" in failed_run["error_message"]

            mixed_sources = payload.model_copy(deep=True)
            mixed_sources.variants[0].list_price_eur = 17500
            mixed_sources.sources.append(
                mixed_sources.sources[0].model_copy(
                    update={
                        "source_key": "drivewise-synthetic-eea",
                        "name": "Drivewise Synthetic EEA Fixture",
                        "source_type": "public_dataset",
                        "url": "https://example.test/eea/catalog",
                    }
                )
            )
            mixed_sources.variants[0].provenance_claims = [
                ProvenanceClaim(
                    source_key="drivewise-synthetic-catalog",
                    source_url="https://example.test/local/acme-metro",
                    observed_at=datetime.fromisoformat("2026-07-16T09:00:00+02:00"),
                    supported_metrics=[
                        "variant_key",
                        "vehicle_key",
                        "trim",
                        "is_default",
                        "body_style",
                        "fuel_type",
                        "list_price_eur",
                        "drivetrain",
                        "transmission",
                        "engine",
                        "horsepower",
                        "seats",
                        "cargo_volume_liters",
                    ],
                ),
                ProvenanceClaim(
                    source_key="drivewise-synthetic-eea",
                    source_url="https://example.test/eea/acme-metro",
                    observed_at=datetime.fromisoformat("2026-06-30T09:00:00+02:00"),
                    supported_metrics=[
                        "consumption_l_100km",
                        "co2_g_km",
                        "euro_emission_standard",
                    ],
                ),
            ]
            import_catalog(
                conn,
                mixed_sources,
                file_name="pytest-catalog-mixed-provenance.json",
            )
            mixed_claims = conn.execute(
                """
                SELECT source.source_key, provenance.is_current
                FROM vehicle_spec_provenance provenance
                JOIN sources source ON source.id = provenance.source_id
                JOIN vehicle_specs spec ON spec.id = provenance.spec_id
                WHERE spec.variant_key = 'it-acme-metro-2026-petrol'
                ORDER BY source.source_key
                """
            ).fetchall()
            assert mixed_claims == [
                {
                    "source_key": "drivewise-synthetic-catalog",
                    "is_current": True,
                },
                {
                    "source_key": "drivewise-synthetic-eea",
                    "is_current": True,
                },
            ]

            source_b_current = mixed_sources.model_copy(deep=True)
            source_b_current.vehicles[0].source_key = "drivewise-synthetic-eea"
            source_b_current.vehicles[0].source_url = (
                "https://example.test/eea/acme-metro"
            )
            source_b_current.vehicles[0].observed_at = datetime.fromisoformat(
                "2026-07-17T09:00:00+02:00"
            )
            source_b_current.vehicles[0].provenance_claims = []
            for variant in source_b_current.variants:
                variant.source_key = "drivewise-synthetic-eea"
                variant.source_url = "https://example.test/eea/acme-metro"
                variant.observed_at = datetime.fromisoformat(
                    "2026-07-17T09:00:00+02:00"
                )
                variant.provenance_claims = []
            source_b_current.variants[0].list_price_eur = 18100
            import_catalog(
                conn,
                source_b_current,
                file_name="pytest-catalog-source-b-current.json",
            )
            current_claims = conn.execute(
                """
                SELECT source.source_key, provenance.is_current
                FROM vehicle_spec_provenance provenance
                JOIN sources source ON source.id = provenance.source_id
                JOIN vehicle_specs spec ON spec.id = provenance.spec_id
                WHERE spec.variant_key = 'it-acme-metro-2026-petrol'
                ORDER BY source.source_key
                """
            ).fetchall()
            assert current_claims == [
                {
                    "source_key": "drivewise-synthetic-catalog",
                    "is_current": False,
                },
                {
                    "source_key": "drivewise-synthetic-eea",
                    "is_current": True,
                },
            ]

            stale_listing = source_b_current.model_copy(deep=True)
            stale_listing.listings[0].observed_at = datetime.fromisoformat(
                "2026-07-15T09:00:00+02:00"
            )
            stale_listing.listings[0].price_eur = 12345
            stale_listing.listings[0].is_active = False
            with pytest.raises(CatalogValidationError, match="listing .* is older"):
                import_catalog(
                    conn,
                    stale_listing,
                    file_name="pytest-catalog-stale-listing.json",
                )
            unchanged_listing = conn.execute(
                """
                SELECT price_eur, is_active
                FROM listings
                WHERE listing_ref = 'synthetic-acme-metro-petrol-new'
                  AND source_id = (
                    SELECT id FROM sources
                    WHERE source_key = 'drivewise-synthetic-catalog'
                  )
                """
            ).fetchone()
            assert float(unchanged_listing["price_eur"]) == 9500
            assert unchanged_listing["is_active"] is True

            stale_vehicle = source_b_current.model_copy(deep=True)
            stale_vehicle.vehicles[0].observed_at = datetime.fromisoformat(
                "2026-07-16T09:00:00+02:00"
            )
            stale_vehicle.vehicles[0].model = "Stale overwrite"
            with pytest.raises(CatalogValidationError, match="vehicle .* is older"):
                import_catalog(
                    conn,
                    stale_vehicle,
                    file_name="pytest-catalog-stale-vehicle.json",
                )

            stale_variant = source_b_current.model_copy(deep=True)
            stale_variant.variants[0].observed_at = datetime.fromisoformat(
                "2026-07-16T09:00:00+02:00"
            )
            stale_variant.variants[0].list_price_eur = 9999
            with pytest.raises(CatalogValidationError, match="variant .* is older"):
                import_catalog(
                    conn,
                    stale_variant,
                    file_name="pytest-catalog-stale-variant.json",
                )
            current_values = conn.execute(
                """
                SELECT vehicle.model, spec.list_price_eur
                FROM vehicle_specs spec
                JOIN vehicles vehicle ON vehicle.id = spec.vehicle_id
                WHERE spec.variant_key = 'it-acme-metro-2026-petrol'
                """
            ).fetchone()
            assert current_values["model"] == "Metro"
            assert float(current_values["list_price_eur"]) == 18100
        finally:
            _cleanup_catalog_test_rows(conn)


def _cleanup_catalog_test_rows(conn) -> None:
    fixture_hash = compute_catalog_hash(load_catalog(FIXTURE_PATH))
    conn.execute(
        """
        DELETE FROM import_runs
        WHERE file_name LIKE 'pytest-catalog-%%' OR dataset_hash = %s
        """,
        (fixture_hash,),
    )
    sources = conn.execute(
        """
        SELECT id FROM sources
        WHERE source_key IN (
          'drivewise-synthetic-catalog',
          'drivewise-synthetic-eea'
        )
        """
    ).fetchall()
    for source in sources:
        conn.execute("DELETE FROM listings WHERE source_id = %s", (source["id"],))
    conn.execute(
        """
        DELETE FROM vehicles
        WHERE canonical_key IN ('it-acme-metro-2026', 'it-acme-overflow-2026')
        """
    )
    for source in sources:
        conn.execute(
            """
            DELETE FROM sources source
            WHERE source.id = %s
              AND NOT EXISTS (
                SELECT 1 FROM vehicle_provenance WHERE source_id = source.id
              )
              AND NOT EXISTS (
                SELECT 1 FROM vehicle_spec_provenance WHERE source_id = source.id
              )
              AND NOT EXISTS (SELECT 1 FROM listings WHERE source_id = source.id)
              AND NOT EXISTS (
                SELECT 1 FROM vehicle_maintenance_items WHERE source_id = source.id
              )
              AND NOT EXISTS (
                SELECT 1 FROM vehicle_safety_ratings WHERE source_id = source.id
              )
              AND NOT EXISTS (
                SELECT 1 FROM vehicle_features WHERE source_id = source.id
              )
              AND NOT EXISTS (
                SELECT 1 FROM vehicle_media_assets WHERE source_id = source.id
              )
            """,
            (source["id"],),
        )
