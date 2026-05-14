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

## Migration Files

- `apps/api/migrations/0001_enable_pgvector.sql` enables pgvector.
- `apps/api/migrations/0002_create_mvp_schema.sql` creates the MVP schema.
- `apps/api/migrations/0003_seed_initial_vehicles.sql` inserts synthetic seed data.

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
- `make`
- `model`
- `model_year`
- `body_style`
- `fuel_type`
- `market` with values such as `IT` or `EU`
- `base_price_eur`

Uniqueness is enforced on `(make, model, model_year, market)`.

### vehicle_specs

Structured specs for a vehicle trim.

Key columns:

- `vehicle_id`
- `trim`
- `drivetrain`
- `transmission`
- `engine`
- `horsepower`
- `battery_kwh`
- `consumption_l_100km`
- `wltp_range_km`
- `co2_g_km`
- `euro_emission_standard`
- `cargo_volume_liters`
- `metadata jsonb`

Uniqueness is enforced on `(vehicle_id, trim)`.

### sources

Metadata for where records came from.

Allowed source types:

- `manual_seed`
- `public_dataset`
- `curated_internal`

Real Firecrawl source rows are intentionally excluded until crawling is implemented. The current Firecrawl planner validates source configuration without changing schema or writing rows.

### listings

Synthetic or future ingested market listings tied to a vehicle and source.

Key columns:

- `vehicle_id`
- `source_id`
- `listing_ref`
- `title`
- `price_eur`
- `mileage`, stored as odometer kilometres for EU/IT seed data
- `condition`
- `location_region`
- `raw_payload jsonb`

Uniqueness is enforced on `(source_id, listing_ref)`.

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
- `rank`
- `score`
- `rationale`

Uniqueness is enforced on `(run_id, rank)` and `(run_id, vehicle_id)`.

The MVP stores score and rationale in this table. Detailed evidence is returned by the API response but is not persisted in the current schema.

## Seed Data

The seed migration inserts 5 synthetic but realistic Italian/European market vehicle records:

- 2024 Fiat Panda
- 2024 Toyota Yaris Hybrid
- 2024 Volkswagen Golf
- 2024 Dacia Sandero
- 2024 Tesla Model 3

Each seed vehicle has one spec row, one listing row, and one document row. Seed values are illustrative and not authoritative.
