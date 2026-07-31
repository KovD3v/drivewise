# Drivewise Data Model

## Scope

The MVP data model stores synthetic vehicle records, basic specs, source metadata, listing snapshots, document text, and deterministic advisor recommendation outputs.

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

`POST /advisor/recommendations` writes one row per recommendation run.

### recommendation_items

Stores ranked deterministic advisor output items.

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
