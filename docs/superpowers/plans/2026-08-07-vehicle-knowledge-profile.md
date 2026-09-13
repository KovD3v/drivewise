# Vehicle Knowledge Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `GET /vehicles/{vehicle_id}` with a persisted, source-aware technical knowledge profile for each variant and prove one synthetic variant end-to-end.

**Architecture:** Keep PostgreSQL as the source of truth. Store single-valued technical facts on `vehicle_specs`, store repeating maintenance, safety, feature, and media facts in relational child tables, extend curated catalog ingestion, and compose additive nested response sections in the vehicle repository without N+1 queries.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, psycopg 3, PostgreSQL/Neon, pytest, Ruff, JSON Schema.

## Global Constraints

- Preserve the existing `GET /vehicles/{vehicle_id}` route and every current flat `VehicleSpec` response field.
- Do not add insurance, vehicle tax, real-world consumption, reliability, known defects, recalls, compatibility, valuation, depreciation, fuel-cost, or recommendation fields.
- Do not add Neo4j, Firecrawl, Redis, an external service, or a new runtime dependency.
- All fixture facts and URLs must remain synthetic.
- Missing scalar facts serialize as `null`; missing repeating resources serialize as `[]`.
- An omitted curated-catalog child collection means no update; an explicit empty collection clears that collection.
- Implement each runtime behavior test-first and observe the expected failure before adding production code.
- Stage and commit only files listed in the active task.

---

## File Structure

- `apps/api/migrations/0005_vehicle_knowledge_profile.sql`: scalar variant columns and four relational child tables.
- `apps/api/app/ingestion/catalog.py`: validated catalog input models, cross-reference validation, scalar upsert expansion, and child collection synchronization.
- `apps/api/app/schemas/vehicles.py`: additive nested API response models.
- `apps/api/app/repositories/vehicles.py`: bounded profile queries, grouping, and response composition.
- `apps/api/pyproject.toml`, `apps/api/uv.lock`: JSON Schema test-only dependency and lock state.
- `apps/api/tests/test_migrations.py`: static and live migration coverage.
- `apps/api/tests/test_catalog_import.py`: catalog validation and persistence behavior.
- `apps/api/tests/test_vehicle_listing_api.py`: response serialization and compatibility behavior.
- `data/fixtures/catalog/catalog-v1.synthetic.json`: one complete synthetic profile on `it-acme-metro-2026-petrol`.
- `docs/catalog-v1.schema.json`: additive catalog input schema.
- `docs/api-contract.md`, `docs/data-model.md`, `docs/catalog-import.md`: durable contract documentation.

---

### Task 1: Add the relational vehicle-profile schema

**Files:**

- Create: `apps/api/migrations/0005_vehicle_knowledge_profile.sql`
- Modify: `apps/api/tests/test_migrations.py`

**Interfaces:**

- Consumes: existing `vehicle_specs(id)`, `sources(id)`, and ordered migration runner.
- Produces: nullable scalar profile columns plus `vehicle_maintenance_items`, `vehicle_safety_ratings`, `vehicle_features`, and `vehicle_media_assets`.

- [ ] **Step 1: Write the failing migration inventory test**

Add `0005_vehicle_knowledge_profile.sql` to the exact ordered-name assertion,
add the four child tables to `REQUIRED_TABLES`, and add this focused test:

```python
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
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
uv run --project apps/api pytest apps/api/tests/test_migrations.py::test_migration_files_are_ordered apps/api/tests/test_migrations.py::test_vehicle_knowledge_profile_migration_is_relational_and_constrained -q
```

Expected: failures because `0005_vehicle_knowledge_profile.sql` does not exist
and the ordered migration list ends at `0004_curated_catalog.sql`.

- [ ] **Step 3: Create the migration**

Use idempotent `ADD COLUMN IF NOT EXISTS` statements with positive checks, then
create the tables with this exact ownership model:

```sql
ALTER TABLE vehicle_specs
  ADD COLUMN IF NOT EXISTS generation_name text,
  ADD COLUMN IF NOT EXISTS restyling_label text,
  ADD COLUMN IF NOT EXISTS category text,
  ADD COLUMN IF NOT EXISTS doors integer,
  ADD COLUMN IF NOT EXISTS length_mm integer,
  ADD COLUMN IF NOT EXISTS width_mm integer,
  ADD COLUMN IF NOT EXISTS height_mm integer,
  ADD COLUMN IF NOT EXISTS wheelbase_mm integer,
  ADD COLUMN IF NOT EXISTS curb_weight_kg integer,
  ADD COLUMN IF NOT EXISTS gross_weight_kg integer,
  ADD COLUMN IF NOT EXISTS payload_kg integer,
  ADD COLUMN IF NOT EXISTS engine_code text,
  ADD COLUMN IF NOT EXISTS displacement_cc integer,
  ADD COLUMN IF NOT EXISTS cylinders integer,
  ADD COLUMN IF NOT EXISTS power_kw numeric(7, 2),
  ADD COLUMN IF NOT EXISTS torque_nm integer,
  ADD COLUMN IF NOT EXISTS battery_usable_kwh numeric(7, 2),
  ADD COLUMN IF NOT EXISTS transmission_type text,
  ADD COLUMN IF NOT EXISTS gear_count integer,
  ADD COLUMN IF NOT EXISTS differential_type text,
  ADD COLUMN IF NOT EXISTS acceleration_0_100_s numeric(5, 2),
  ADD COLUMN IF NOT EXISTS top_speed_kmh integer,
  ADD COLUMN IF NOT EXISTS braking_100_0_m numeric(5, 2),
  ADD COLUMN IF NOT EXISTS homologation_cycle text;

ALTER TABLE vehicle_specs
  ADD CONSTRAINT vehicle_specs_doors_check CHECK (doors IS NULL OR doors > 0),
  ADD CONSTRAINT vehicle_specs_dimensions_check CHECK (
    (length_mm IS NULL OR length_mm > 0)
    AND (width_mm IS NULL OR width_mm > 0)
    AND (height_mm IS NULL OR height_mm > 0)
    AND (wheelbase_mm IS NULL OR wheelbase_mm > 0)
  ),
  ADD CONSTRAINT vehicle_specs_weights_check CHECK (
    (curb_weight_kg IS NULL OR curb_weight_kg > 0)
    AND (gross_weight_kg IS NULL OR gross_weight_kg > 0)
    AND (payload_kg IS NULL OR payload_kg >= 0)
  ),
  ADD CONSTRAINT vehicle_specs_powertrain_profile_check CHECK (
    (displacement_cc IS NULL OR displacement_cc > 0)
    AND (cylinders IS NULL OR cylinders > 0)
    AND (power_kw IS NULL OR power_kw > 0)
    AND (torque_nm IS NULL OR torque_nm > 0)
    AND (battery_usable_kwh IS NULL OR battery_usable_kwh > 0)
  ),
  ADD CONSTRAINT vehicle_specs_transmission_profile_check CHECK (
    gear_count IS NULL OR gear_count > 0
  ),
  ADD CONSTRAINT vehicle_specs_performance_profile_check CHECK (
    (acceleration_0_100_s IS NULL OR acceleration_0_100_s > 0)
    AND (top_speed_kmh IS NULL OR top_speed_kmh > 0)
    AND (braking_100_0_m IS NULL OR braking_100_0_m > 0)
  );

CREATE TABLE IF NOT EXISTS vehicle_maintenance_items (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE CASCADE,
  operation_code text NOT NULL,
  title text NOT NULL,
  interval_km integer,
  interval_months integer,
  notes text,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicle_maintenance_source_https_check CHECK (
    source_url LIKE 'https://%'
  ),
  CONSTRAINT vehicle_maintenance_interval_check CHECK (
    (interval_km IS NOT NULL AND interval_km > 0)
    OR (interval_months IS NOT NULL AND interval_months > 0)
  ),
  UNIQUE (spec_id, operation_code)
);

CREATE TABLE IF NOT EXISTS vehicle_safety_ratings (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE CASCADE,
  assessment_system text NOT NULL,
  assessment_year integer NOT NULL CHECK (assessment_year BETWEEN 1990 AND 2100),
  overall_stars integer CHECK (overall_stars BETWEEN 0 AND 5),
  adult_occupant_percent integer CHECK (adult_occupant_percent BETWEEN 0 AND 100),
  child_occupant_percent integer CHECK (child_occupant_percent BETWEEN 0 AND 100),
  vulnerable_road_users_percent integer CHECK (vulnerable_road_users_percent BETWEEN 0 AND 100),
  safety_assist_percent integer CHECK (safety_assist_percent BETWEEN 0 AND 100),
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicle_safety_ratings_source_https_check CHECK (
    source_url LIKE 'https://%'
  ),
  UNIQUE (spec_id, assessment_system, assessment_year)
);

CREATE TABLE IF NOT EXISTS vehicle_features (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE CASCADE,
  feature_key text NOT NULL,
  category text NOT NULL,
  name text NOT NULL,
  availability text NOT NULL,
  notes text,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicle_features_source_https_check CHECK (
    source_url LIKE 'https://%'
  ),
  CONSTRAINT vehicle_features_category_check CHECK (
    category IN ('adas', 'safety', 'technology', 'comfort')
  ),
  CONSTRAINT vehicle_features_availability_check CHECK (
    availability IN ('standard', 'optional')
  ),
  UNIQUE (spec_id, feature_key)
);

CREATE TABLE IF NOT EXISTS vehicle_media_assets (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE CASCADE,
  asset_key text NOT NULL,
  asset_type text NOT NULL,
  title text NOT NULL,
  url text NOT NULL,
  mime_type text,
  locale text,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicle_media_assets_type_check CHECK (
    asset_type IN ('photo', 'brochure', 'manual')
  ),
  CONSTRAINT vehicle_media_assets_source_https_check CHECK (
    source_url LIKE 'https://%'
  ),
  CONSTRAINT vehicle_media_assets_https_check CHECK (url LIKE 'https://%'),
  UNIQUE (spec_id, asset_key)
);

CREATE INDEX IF NOT EXISTS vehicle_maintenance_items_spec_id_idx
  ON vehicle_maintenance_items (spec_id);
CREATE INDEX IF NOT EXISTS vehicle_safety_ratings_spec_id_idx
  ON vehicle_safety_ratings (spec_id);
CREATE INDEX IF NOT EXISTS vehicle_features_spec_id_category_idx
  ON vehicle_features (spec_id, category);
CREATE INDEX IF NOT EXISTS vehicle_media_assets_spec_id_idx
  ON vehicle_media_assets (spec_id);
```

- [ ] **Step 4: Run migration tests and verify GREEN**

Run:

```bash
uv run --project apps/api pytest apps/api/tests/test_migrations.py -q
```

Expected: all configured tests pass; database-dependent tests may report the
existing skip when `TEST_DATABASE_URL` is absent.

- [ ] **Step 5: Commit the schema task**

```bash
git add apps/api/migrations/0005_vehicle_knowledge_profile.sql apps/api/tests/test_migrations.py
git commit -m "feat(api): add vehicle knowledge profile schema"
```

---

### Task 2: Extend the curated catalog contract

**Files:**

- Modify: `apps/api/app/ingestion/catalog.py`
- Modify: `apps/api/tests/test_catalog_import.py`
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/api/uv.lock`
- Modify: `docs/catalog-v1.schema.json`
- Modify: `data/fixtures/catalog/catalog-v1.synthetic.json`

**Interfaces:**

- Consumes: `VariantRecord`, declared `SourceRecord` keys, and catalog v1 strict validation.
- Produces: `MaintenanceRecord`, `SafetyRatingRecord`, `FeatureRecord`, and `MediaRecord`; optional child collections use `model_fields_set` to distinguish omission from explicit clearing.

- [ ] **Step 1: Write failing catalog-model tests**

Add `jsonschema>=4.23.0` to the existing `dev` dependency group and refresh the
lock with `uv lock --project apps/api`. Add tests that assert the checked-in
JSON Schema is valid and accepts the enriched fixture, the enriched fixture
loads through Pydantic, one variant contains every
new collection, omission is distinguishable from an explicit empty array, a
maintenance item without either interval is rejected, an unknown child source
is rejected, duplicate keys within one variant are rejected, and an HTTP media
URL is rejected.

Use these central assertions:

```python
def test_catalog_loads_complete_vehicle_profile_fixture():
    payload = load_catalog(FIXTURE_PATH)
    variant = next(
        item for item in payload.variants
        if item.variant_key == "it-acme-metro-2026-petrol"
    )

    assert variant.engine_code == "SYN-T10"
    assert variant.power_kw == 74
    assert len(variant.maintenance_schedule) == 2
    assert len(variant.safety_ratings) == 1
    assert {item.category for item in variant.features} == {
        "adas", "safety", "technology", "comfort"
    }
    assert {item.asset_type for item in variant.media} == {
        "photo", "brochure", "manual"
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
    cleared = unenriched.model_copy(
        update={"maintenance_schedule": []}
    )
    cleared.__pydantic_fields_set__.add("maintenance_schedule")
    assert "maintenance_schedule" in cleared.model_fields_set
```

- [ ] **Step 2: Run the focused catalog tests and verify RED**

Run:

```bash
uv run --project apps/api pytest apps/api/tests/test_catalog_import.py -k "vehicle_profile or profile_collections" -q
```

Expected: failure because `VariantRecord` has no profile fields or child
collection models.

- [ ] **Step 3: Add strict Pydantic input models**

Add a shared child-source base and exact bounded models:

```python
class ChildSourceRecord(StrictModel):
    source_key: str = Field(min_length=1, max_length=160)
    source_url: str
    observed_at: datetime

    @field_validator("source_key")
    @classmethod
    def validate_source_key(cls, value: str) -> str:
        return _validate_key(value, "source_key")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        url = _validate_url(value)
        if not url.startswith("https://"):
            raise ValueError("child source URL must use https")
        return url

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value


class MaintenanceRecord(ChildSourceRecord):
    operation_code: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    interval_km: int | None = Field(default=None, gt=0)
    interval_months: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_interval(self):
        if self.interval_km is None and self.interval_months is None:
            raise ValueError("maintenance item requires an interval")
        return self


class SafetyRatingRecord(ChildSourceRecord):
    assessment_system: str = Field(min_length=1, max_length=80)
    assessment_year: int = Field(ge=1990, le=2100)
    overall_stars: int | None = Field(default=None, ge=0, le=5)
    adult_occupant_percent: int | None = Field(default=None, ge=0, le=100)
    child_occupant_percent: int | None = Field(default=None, ge=0, le=100)
    vulnerable_road_users_percent: int | None = Field(default=None, ge=0, le=100)
    safety_assist_percent: int | None = Field(default=None, ge=0, le=100)


class FeatureRecord(ChildSourceRecord):
    feature_key: str = Field(min_length=1, max_length=160)
    category: Literal["adas", "safety", "technology", "comfort"]
    name: str = Field(min_length=1, max_length=240)
    availability: Literal["standard", "optional"]
    notes: str | None = Field(default=None, max_length=500)


class MediaRecord(ChildSourceRecord):
    asset_key: str = Field(min_length=1, max_length=160)
    asset_type: Literal["photo", "brochure", "manual"]
    title: str = Field(min_length=1, max_length=240)
    url: str
    mime_type: str | None = Field(default=None, max_length=120)
    locale: str | None = Field(default=None, max_length=20)

    @field_validator("url")
    @classmethod
    def require_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("media URL must use https")
        return value
```

Add the spec's optional scalar fields to `VariantRecord` with positive bounds.
Add all four child collections with `Field(default_factory=list)` so
`model_fields_set` retains omission information.

- [ ] **Step 4: Extend cross-reference and uniqueness validation**

In `validate_catalog`, validate every child `source_key` against the declared
source set and require unique keys per variant:

```python
for variant in payload.variants:
    child_groups = [
        ("maintenance operation_code", variant.maintenance_schedule, "operation_code"),
        ("safety assessment", variant.safety_ratings, None),
        ("feature_key", variant.features, "feature_key"),
        ("media asset_key", variant.media, "asset_key"),
    ]
    for label, records, key_name in child_groups:
        for record in records:
            if record.source_key not in source_keys:
                raise CatalogValidationError(
                    f"{label} references unknown source_key: {record.source_key}"
                )
        if key_name is not None:
            _require_unique(
                f"{variant.variant_key} {label}",
                [getattr(record, key_name) for record in records],
            )
    _require_unique(
        f"{variant.variant_key} safety assessment",
        [
            f"{record.assessment_system}:{record.assessment_year}"
            for record in variant.safety_ratings
        ],
    )
```

- [ ] **Step 5: Extend the JSON Schema and synthetic fixture**

Add an `httpsUrl` definition plus the same scalar constraints and `$defs` child objects to
`docs/catalog-v1.schema.json`. All child objects use
`additionalProperties: false`; every child requires `source_key`, `source_url`,
and `observed_at`; child `source_url` and media `url` reference `httpsUrl`.

Enrich only `it-acme-metro-2026-petrol` with the values shown in the approved
design, two maintenance operations, one synthetic Euro NCAP rating, four
features covering all categories, and one synthetic HTTPS asset for each media
type. Add every new non-null scalar field to that variant's
`provenance_claims.supported_metrics`.

- [ ] **Step 6: Run catalog validation tests and verify GREEN**

Run:

```bash
uv run --project apps/api pytest apps/api/tests/test_catalog_import.py -k "catalog and not write" -q
uv run --project apps/api python apps/api/scripts/import_catalog.py --path data/fixtures/catalog/catalog-v1.synthetic.json --check
```

Expected: focused tests pass and the CLI prints `Catalog is valid.` without a
database connection.

- [ ] **Step 7: Commit the catalog-contract task**

```bash
git add apps/api/app/ingestion/catalog.py apps/api/tests/test_catalog_import.py apps/api/pyproject.toml apps/api/uv.lock docs/catalog-v1.schema.json data/fixtures/catalog/catalog-v1.synthetic.json
git commit -m "feat(api): define curated vehicle profile input"
```

---

### Task 3: Persist scalar and repeating profile facts transactionally

**Files:**

- Modify: `apps/api/app/ingestion/catalog.py`
- Modify: `apps/api/tests/test_catalog_import.py`

**Interfaces:**

- Consumes: validated `VariantRecord` profile fields, `variant_ids`, and `source_ids`.
- Produces: `_sync_variant_profile_children(conn, variant, spec_id, source_ids)` and deterministic child UUIDs.

- [ ] **Step 1: Write a failing database import test**

Inside the existing `TEST_DATABASE_URL`-guarded catalog test, assert after the
first import that the enriched spec has `engine_code = 'SYN-T10'`, two
maintenance items, one safety rating, four features, and three media assets.
Then import a changed payload where `maintenance_schedule` is omitted and prove
the two rows remain. Import another changed payload with
`maintenance_schedule = []` and prove the rows are deleted. Re-import the final
payload and prove counts and rows remain stable.

Use direct SQL counts scoped through `variant_key =
'it-acme-metro-2026-petrol'`; do not assert global table counts.

- [ ] **Step 2: Run the database test and verify RED**

Run with the same disposable pgvector database convention used by the existing
suite:

```bash
TEST_DATABASE_URL="$TEST_DATABASE_URL" uv run --project apps/api pytest apps/api/tests/test_catalog_import.py::test_catalog_write_is_idempotent_updates_and_rolls_back_atomically -q
```

Expected: failure on missing profile columns or missing child rows.

- [ ] **Step 3: Expand the scalar variant upsert**

Add every new scalar column to the `INSERT INTO vehicle_specs`, `VALUES`, and
conflict-update clauses in `_upsert_variants`. Pass values in the
same column order. Because `_content_hash(variant.model_dump(mode="json"))`
already includes the additive fields and child arrays, profile changes remain
part of idempotency and stale-write detection.

- [ ] **Step 4: Add deterministic child synchronization**

Define one UUID namespace constant per child table. Call this function after
each variant upsert:

```python
def _sync_variant_profile_children(
    conn,
    variant: VariantRecord,
    spec_id: UUID,
    source_ids: dict[str, UUID],
) -> None:
    configurations = [
        (
            "maintenance_schedule",
            "vehicle_maintenance_items",
            variant.maintenance_schedule,
            lambda record: record.operation_code,
            _upsert_maintenance_item,
        ),
        (
            "safety_ratings",
            "vehicle_safety_ratings",
            variant.safety_ratings,
            lambda record: f"{record.assessment_system}:{record.assessment_year}",
            _upsert_safety_rating,
        ),
        (
            "features",
            "vehicle_features",
            variant.features,
            lambda record: record.feature_key,
            _upsert_feature,
        ),
        (
            "media",
            "vehicle_media_assets",
            variant.media,
            lambda record: record.asset_key,
            _upsert_media_asset,
        ),
    ]
    for field_name, table, records, key_function, upsert in configurations:
        if field_name not in variant.model_fields_set:
            continue
        retained_ids = [
            upsert(conn, spec_id, record, source_ids[record.source_key])
            for record in records
        ]
        if retained_ids:
            conn.execute(
                f"DELETE FROM {table} WHERE spec_id = %s AND id <> ALL(%s)",
                (spec_id, retained_ids),
            )
        else:
            conn.execute(f"DELETE FROM {table} WHERE spec_id = %s", (spec_id,))
```

Each `_upsert_*` helper derives its UUID from `spec_id`, stable key, and table
namespace, inserts every domain field plus `source_id`, `source_url`, and
`observed_at`, updates all mutable fields on its unique-key conflict, and
returns the deterministic UUID. Keep table names internal constants; never
accept them from request or catalog data.

- [ ] **Step 5: Run the focused database test and verify GREEN**

Run:

```bash
TEST_DATABASE_URL="$TEST_DATABASE_URL" uv run --project apps/api pytest apps/api/tests/test_catalog_import.py::test_catalog_write_is_idempotent_updates_and_rolls_back_atomically -q
```

Expected: pass with omission preserving rows, explicit empty clearing rows,
and re-import remaining idempotent.

- [ ] **Step 6: Run all catalog-import tests**

```bash
TEST_DATABASE_URL="$TEST_DATABASE_URL" uv run --project apps/api pytest apps/api/tests/test_catalog_import.py -q
```

Expected: all tests pass with no traceback or warnings introduced by this task.

- [ ] **Step 7: Commit the persistence task**

```bash
git add apps/api/app/ingestion/catalog.py apps/api/tests/test_catalog_import.py
git commit -m "feat(api): persist curated vehicle profiles"
```

---

### Task 4: Expose the additive vehicle-detail response

**Files:**

- Modify: `apps/api/app/schemas/vehicles.py`
- Modify: `apps/api/app/repositories/vehicles.py`
- Modify: `apps/api/tests/test_vehicle_listing_api.py`
- Modify: `apps/api/tests/test_migrations.py`

**Interfaces:**

- Consumes: profile columns and child tables from Tasks 1 and 3.
- Produces: nested `identity`, `dimensions`, `powertrain`, `transmission_details`, `performance`, `official_efficiency`, `maintenance_schedule`, `safety`, `technology_comfort`, and `media` fields on `VehicleSpec`.

- [ ] **Step 1: Write the failing API serialization test**

Enrich the fake repository's Fiat specification with one record per nested
resource and assert:

```python
def test_get_vehicle_returns_complete_knowledge_profile(client):
    response = client.get(f"/vehicles/{FIAT_ID}")

    assert response.status_code == 200
    spec = response.json()["specs"][0]
    assert spec["identity"]["generation_name"] == "Third generation"
    assert spec["dimensions"]["curb_weight_kg"] == 980
    assert spec["powertrain"]["engine_code"] == "SYN-F10"
    assert spec["transmission_details"]["gear_count"] == 6
    assert spec["performance"]["power_to_weight_kw_per_t"] == 52.04
    assert spec["official_efficiency"]["homologation_cycle"] == "WLTP"
    assert spec["maintenance_schedule"][0]["operation_code"] == "engine-oil"
    assert spec["safety"]["ratings"][0]["overall_stars"] == 4
    assert spec["safety"]["adas"][0]["feature_key"] == "lane-support"
    assert spec["technology_comfort"][0]["category"] == "comfort"
    assert spec["media"][0]["asset_type"] == "manual"

    assert spec["engine"] == "1.0L mild-hybrid petrol"
    assert spec["consumption_l_100km"] == 5.0
```

Add a separate response-model test that validates an old flat specification and
asserts nested scalar sections contain `null` while every collection is `[]`.

- [ ] **Step 2: Run the API tests and verify RED**

```bash
uv run --project apps/api pytest apps/api/tests/test_vehicle_listing_api.py -k "knowledge_profile or empty_profile" -q
```

Expected: failure because `VehicleSpec` drops the unknown nested keys or does
not provide the new defaults.

- [ ] **Step 3: Add exact response models**

Create focused Pydantic models for each section. Use default factories
for nested sections and lists. Use one narrow `ProfileProvenance` model for child
facts. Add a computed validator or repository calculation so
`power_to_weight_kw_per_t` is rounded to two decimals and is `None` when either
input is unavailable.

The top-level additive fields on `VehicleSpec` are exactly:

```python
identity: VehicleIdentity = Field(default_factory=VehicleIdentity)
dimensions: VehicleDimensions = Field(default_factory=VehicleDimensions)
powertrain: VehiclePowertrain = Field(default_factory=VehiclePowertrain)
transmission_details: VehicleTransmission = Field(
    default_factory=VehicleTransmission
)
performance: VehiclePerformance = Field(default_factory=VehiclePerformance)
official_efficiency: VehicleOfficialEfficiency = Field(
    default_factory=VehicleOfficialEfficiency
)
maintenance_schedule: list[VehicleMaintenanceItem] = Field(default_factory=list)
safety: VehicleSafety = Field(default_factory=VehicleSafety)
technology_comfort: list[VehicleFeature] = Field(default_factory=list)
media: list[VehicleMediaAsset] = Field(default_factory=list)
```

- [ ] **Step 4: Extend the repository with bounded queries**

Select all new scalar columns in the existing spec query. After loading specs,
run exactly four additional queries, each using:

```sql
WHERE child.spec_id = ANY(%s)
ORDER BY child.spec_id, child.created_at, child.id
```

Join `sources` in every query and alias source fields to the
`ProfileProvenance` names. Group rows by `spec_id`. Compose the nested sections
from existing and new scalar fields. Split feature rows by category:

```python
adas = [row for row in features if row["category"] == "adas"]
safety_equipment = [row for row in features if row["category"] == "safety"]
technology_comfort = [
    row for row in features
    if row["category"] in {"technology", "comfort"}
]
```

Calculate the ratio as:

```python
power_to_weight = None
if spec["power_kw"] is not None and spec["curb_weight_kg"]:
    power_to_weight = round(
        float(spec["power_kw"]) * 1000 / spec["curb_weight_kg"],
        2,
    )
```

Remove internal raw scalar keys from the returned dict only when they are not
part of the existing flat contract. Preserve all existing flat keys.

- [ ] **Step 5: Add a live repository assertion**

In the database-backed migration test, call
`VehiclesRepository(conn).get_vehicle(enriched_vehicle_id)` after importing the
synthetic catalog and assert the nested profile contains the imported child
rows. This proves the SQL shape, not just fake-repository serialization.

- [ ] **Step 6: Run focused API and repository tests and verify GREEN**

```bash
uv run --project apps/api pytest apps/api/tests/test_vehicle_listing_api.py -q
TEST_DATABASE_URL="$TEST_DATABASE_URL" uv run --project apps/api pytest apps/api/tests/test_migrations.py -q
```

Expected: vehicle/listing API tests pass, live repository assertions pass when
the database is configured, and existing flat contract assertions remain green.

- [ ] **Step 7: Commit the read-contract task**

```bash
git add apps/api/app/schemas/vehicles.py apps/api/app/repositories/vehicles.py apps/api/tests/test_vehicle_listing_api.py apps/api/tests/test_migrations.py
git commit -m "feat(api): expose vehicle knowledge profiles"
```

---

### Task 5: Document and verify the complete backend slice

**Files:**

- Modify: `docs/api-contract.md`
- Modify: `docs/data-model.md`
- Modify: `docs/catalog-import.md`

**Interfaces:**

- Consumes: the final implemented response and persistence behavior.
- Produces: user-facing backend documentation matching runtime names exactly.

- [ ] **Step 1: Update durable documentation**

Document the full enriched `GET /vehicles/{vehicle_id}` response, nullable and
empty-list behavior, all new columns and child tables, child provenance, and
the omitted-versus-explicit-empty catalog collection rule. State the excluded
domains in `docs/api-contract.md` so frontend consumers do not infer that an
absent field is an implementation oversight.

- [ ] **Step 2: Validate docs and fixture consistency**

Run:

```bash
uv run --project apps/api python apps/api/scripts/import_catalog.py --path data/fixtures/catalog/catalog-v1.synthetic.json --check
git diff --check
```

Expected: `Catalog is valid.` and both commands exit `0`.

- [ ] **Step 3: Run the full backend gates**

```bash
uv run --project apps/api ruff check apps/api
uv run --project apps/api pytest apps/api -q
```

When a disposable pgvector database is available, rerun the full suite with
`TEST_DATABASE_URL` set so database tests execute rather than skip.

Expected: Ruff exits `0`; pytest exits `0` with only pre-existing,
environment-gated skips when no test database is configured.

- [ ] **Step 4: Review scope and final diff**

```bash
git status --short
git diff --stat 030b04d..HEAD
git diff --check 030b04d..HEAD
```

Confirm there are no frontend edits, runtime dependency additions, secrets,
real URLs, graph-database code, or excluded domain fields.

- [ ] **Step 5: Commit documentation**

```bash
git add docs/api-contract.md docs/data-model.md docs/catalog-import.md
git commit -m "docs: describe vehicle knowledge profile contract"
```

- [ ] **Step 6: Run final verification after the documentation commit**

```bash
uv run --project apps/api ruff check apps/api
uv run --project apps/api pytest apps/api -q
uv run --project apps/api python apps/api/scripts/import_catalog.py --path data/fixtures/catalog/catalog-v1.synthetic.json --check
git diff --check
git status --short --branch
```

Report exact pass, failure, and skip counts. Distinguish local commits from any
push or deployment; do not push unless separately requested.
