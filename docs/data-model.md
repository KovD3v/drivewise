# Drivewise Data Model

## Scope

The MVP data model stores synthetic vehicle records, basic specs, source metadata, listing snapshots, document text, and deterministic Advisor v3 recommendation outputs.

The schema is oriented to the Italian and European market. Prices are stored in euro, listing odometers are interpreted as kilometres, and technical fields use WLTP and European emissions assumptions.

It is designed for PostgreSQL-compatible Neon databases and enables pgvector with:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Real Firecrawl ingestion, external embedding providers, and production hybrid/vector search are intentionally deferred. Firecrawl has a dry-run planner. Embeddings have a dry-run planner plus a fake-only development write path, and `POST /search/documents` can query those fake vectors only when `mode` is explicitly `vector_fake`.

Local fixture ingestion is documented in `docs/ingestion.md`. It writes normalized fixture content into `documents` and stores conservative extraction proposals in `documents.metadata`.

Reviewed catalog imports are a separate path documented in
`docs/catalog-import.md`. They populate canonical vehicles, purchasable
variants, offers, and record-level provenance without calling external services.

## Migration Files

- `apps/api/migrations/0001_enable_pgvector.sql` enables pgvector.
- `apps/api/migrations/0002_create_mvp_schema.sql` creates the MVP schema.
- `apps/api/migrations/0003_seed_initial_vehicles.sql` inserts synthetic seed data.
- `apps/api/migrations/0004_curated_catalog.sql` adds stable catalog identity,
  variant-linked offers, import runs, and provenance.
- `apps/api/migrations/0006_guided_decisions.sql` persists the current guided
  decision state and append-only per-turn profile snapshots. Version `0005` is
  reserved by the existing vehicle-knowledge-profile design.
- `apps/api/migrations/0005_vehicle_knowledge_profile.sql` adds optional,
  detail-only vehicle-spec knowledge fields and relational child records.
- `apps/api/migrations/0007_https_primary_provenance.sql` validates existing
  primary provenance and rejects non-HTTPS vehicle, spec, and listing URLs.

Run migrations with:

```bash
python apps/api/scripts/migrate.py
```

The script loads local `.env`, reads `DATABASE_URL`, and records applied migrations in `drivewise_schema_migrations`.

## Tables

### vehicles

Canonical vehicle identity for a market and model year.

Key columns:

- `id uuid primary key`
- `canonical_key`, a stable model-year-market import identity
- `model_family_key`, shared by model years and variants in one family
- `make`
- `model`
- `model_year`
- `body_style`
- `fuel_type`
- `market` with values such as `IT` or `EU`
- `base_price_eur`

Uniqueness is enforced on `canonical_key` and on the legacy
`(make, model, model_year, market)` identity. `body_style`, `fuel_type`, and
`base_price_eur` remain compatibility mirrors of the default variant.

### vehicle_specs

Structured purchasable variants for a vehicle.

Key columns:

- `vehicle_id`
- `variant_key`, the stable variant identity
- `is_default`, with at most one default per vehicle
- `trim`
- `body_style`
- `fuel_type`
- `list_price_eur`
- `drivetrain`
- `transmission`
- `engine`
- `horsepower`
- `battery_kwh`
- `energy_consumption_kwh_100km`
- `consumption_l_100km`
- `wltp_range_km`
- `co2_g_km`
- `euro_emission_standard`
- `cargo_volume_liters`
- `metadata jsonb`

Uniqueness is enforced on `variant_key`. Trim names are not identities: two
powertrains may legitimately use the same marketing trim.

The knowledge profile adds nullable detail columns without replacing the
existing flat compatibility fields: `generation_name`, `restyling_label`,
`category`, `doors`; `length_mm`, `width_mm`, `height_mm`, `wheelbase_mm`,
`curb_weight_kg`, `gross_weight_kg`, `payload_kg`; `engine_code`,
`displacement_cc`, `cylinders`, `power_kw`, `torque_nm`,
`battery_usable_kwh`; `transmission_type`, `gear_count`, `differential_type`;
`acceleration_0_100_s`, `top_speed_kmh`, `braking_100_0_m`; and
`homologation_cycle`. Positive-value and valid-dimension/weight checks protect
the applicable numeric fields. The API groups these columns into a detailed
profile only for `GET /vehicles/{vehicle_id}`; no new vehicle identity is
created by profile data.

### Vehicle knowledge-profile child tables

All child tables belong to `vehicle_specs` (`spec_id`) and cascade when that
spec is deleted. They retain a reviewed child-level source through `source_id`,
`source_url`, and `observed_at`, plus `created_at` and `updated_at`; source URLs
are HTTPS and source deletion is restricted.

- `vehicle_maintenance_items`: `id`, `spec_id`, `operation_code`, `title`,
  nullable `interval_km`, `interval_months`, and `notes`, child provenance,
  timestamps. `(spec_id, operation_code)` is unique and at least one positive
  interval is required.
- `vehicle_safety_ratings`: `id`, `spec_id`, `assessment_system`,
  `assessment_year`, nullable `overall_stars`, `adult_occupant_percent`,
  `child_occupant_percent`, `vulnerable_road_users_percent`, and
  `safety_assist_percent`, child provenance, timestamps. Assessment years are
  1990--2100, scores are constrained to their displayed ranges, and
  `(spec_id, assessment_system, assessment_year)` is unique.
- `vehicle_features`: `id`, `spec_id`, `feature_key`, `category`, `name`,
  `availability`, nullable `notes`, child provenance, timestamps.
  `(spec_id, feature_key)` is unique; categories are `adas`, `safety`,
  `technology`, or `comfort`, and availability is `standard` or `optional`.
- `vehicle_media_assets`: `id`, `spec_id`, `asset_key`, `asset_type`, `title`,
  HTTPS `url`, nullable `mime_type` and `locale`, child provenance, timestamps.
  `(spec_id, asset_key)` is unique and types are `photo`, `brochure`, or
  `manual`.

### sources

Metadata for where records came from.

`source_key` is the stable import identity and `market` records the source's
market scope. `ranking_permission` is an explicit trust decision with values
`permitted`, `not_permitted`, or `manual_validation_only`; only `permitted`
sources can contribute offers or metric evidence to rankings. URL, licence, and
notes retain the review basis. Migrated legacy sources default to
`not_permitted`.

Allowed source types:

- `manual_seed`
- `public_dataset`
- `curated_internal`

Real Firecrawl source rows are intentionally excluded until crawling is implemented. The current Firecrawl planner validates source configuration without changing schema or writing rows.

### listings

Synthetic or future ingested market listings tied to a vehicle and source.

Key columns:

- `vehicle_id`
- `spec_id`, nullable only for unresolved legacy rows
- `source_id`
- `listing_ref`
- `title`
- `price_eur`
- `mileage`, stored as odometer kilometres for EU/IT seed data
- `condition`
- `location_region`
- `source_url`, the exact offer URL
- `first_seen_at`, `last_seen_at`, and optional `valid_until`
- `is_active`
- `content_hash`
- `import_run_id`
- `raw_payload jsonb`

Uniqueness is enforced on `(source_id, listing_ref)`.

New curated imports always resolve `spec_id`. A listing omitted from a later
snapshot is left unchanged; only an explicit `is_active: false` deactivates it.
The composite foreign key `(spec_id, vehicle_id)` prevents a listing from being
paired with a variant owned by another vehicle.

### import_runs and provenance

`import_runs` records the v1 dataset hash, file name, status, counts, and a
sanitized failure message. A completed dataset hash is unique, making identical
imports no-ops.

`vehicle_provenance` and `vehicle_spec_provenance` link each imported record to
its reviewed source URL, claim observation time, record observation time,
content hash, import run, current/historical state, and supported metric names.
A record can have several simultaneous current claims so different sources can
support different fields. A new snapshot replaces the entire current claim set;
older snapshots are rejected transactionally rather than overwriting newer
data. Ranking queries accept only current claims from permitted sources.

Profile child provenance is deliberately separate from these record-level
claim tables. Each profile child stores the single source and observation that
supplied it, so a schedule operation, safety assessment, feature, or media
asset can have a different source from its parent variant.

### documents

Text chunks for future retrieval and ranking.

Key columns:

- `source_id`
- `vehicle_id`
- `listing_id`
- `document_type`
- `title`
- `content`
- `embedding vector(1536)`
- `embedding_model`
- `metadata jsonb`

`embedding` is nullable because documents can exist before embedding generation. A partial HNSW cosine index is defined for rows where embeddings are present.

The current write path only supports deterministic local fake vectors through `python apps/api/scripts/embed_documents.py --provider fake --write`. Real external provider embeddings are not implemented.

Local ingestion stores deduplication and parser metadata in `metadata`, including `content_hash`, `local_path`, `proposed_vehicle`, `proposed_listing`, and `unparsed_fields`.

### recommendation_runs

Stores deterministic advisor request metadata.

Key columns:

- `request_payload jsonb`
- `scoring_version`
- `assumptions jsonb`
- `exclusion_counts jsonb`
- `status`
- `notes`
- `created_at`
- `completed_at`

`POST /advisor/recommendations` writes one row per Advisor v3 recommendation
run. `request_payload` contains the normalized profile, defaulted fields,
constraint modes, evaluation timestamp, and active module versions. The run's
`scoring_version` is `advisor-v3.0`; assumptions and exclusion counts preserve
the inputs needed to explain the result.

### guided_decisions and guided_decision_turns

`guided_decisions` stores the current versioned Decision Profile and the last
complete frontend response. `guided_decision_turns` stores the user and
assistant messages, changed field keys, the complete profile snapshot, and the
complete response for every profile version. The `(decision_id,
profile_version)` uniqueness constraint prevents duplicate versions, while the
API's required `expectedProfileVersion` provides optimistic concurrency.

Profile facts are JSONB because the contract is typed and validated at the API
boundary while the field set is expected to evolve. Conversation snapshots are
not treated as the only durable truth: the current profile is stored separately
and every field retains value, confidence, source, confirmation, and update
time.

### recommendation_items

Stores ranked deterministic Advisor v3 output items.

Key columns:

- `run_id`
- `vehicle_id`
- `listing_id`
- `spec_id`
- `condition_group`
- `rank`
- `score`
- `rationale`
- `scoring_version`
- `score_breakdown jsonb`

The breakdown stores `decision_status`, `decision_score`, provisional legacy
`score` behavior, confidence components, structural and preference fit, pillar
scores, penalties, missing factors, module versions, assumptions, evidence,
and provenance. `decision_score` is null for `insufficient_data`; the legacy
`score` can retain provisional Structural Fit for existing clients. Exact
vehicle, listing, and spec identities remain required, so a result cannot be
detached from the offer and variant that produced it.

Rank and vehicle uniqueness are enforced within each new/used condition group,
so one family can appear once in each group without collisions. Legacy V1 rows
use the `legacy` group. A composite foreign key through the selected listing
ensures persisted `vehicle_id`, `listing_id`, and `spec_id` always describe the
same exact offer/variant pair.

## Seed Data

The seed migration inserts 5 synthetic but realistic Italian/European market vehicle records:

- 2024 Fiat Panda
- 2024 Toyota Yaris Hybrid
- 2024 Volkswagen Golf
- 2024 Dacia Sandero
- 2024 Tesla Model 3

Each seed vehicle has one spec row, one listing row, and one document row. Seed values are illustrative and not authoritative.
