# Local Ingestion

Drivewise includes a local ingestion pipeline for synthetic fixture documents and a dry-run planner for future Firecrawl sources. The Firecrawl planner only validates configuration and prints what would be crawled; it does not call Firecrawl, make HTTP requests, write to PostgreSQL, or generate embeddings.

## Fixture Location

Default fixtures live in:

```text
data/fixtures/ingestion/
```

Supported file types:

- `.md`
- `.txt`
- `.json`

The initial fixtures are synthetic and cover Fiat Panda, Toyota Yaris Hybrid, and a Fiat Panda listing.

## Command

Run migrations first, then ingest local fixtures into the database configured by `DATABASE_URL`:

```bash
. .venv/bin/activate
python apps/api/scripts/migrate.py
python apps/api/scripts/ingest_local.py --path data/fixtures/ingestion
```

The command creates or reuses a `sources` row named `Drivewise Local Fixture Ingestion` with source type `curated_internal`, then writes fixture content into `documents`.

## Firecrawl Planning

Firecrawl is prepared but disabled by default. The planning command reads source configuration, checks whether `FIRECRAWL_API_KEY` is present, and prints a dry-run plan:

```bash
python apps/api/scripts/plan_firecrawl.py --sources data/sources.example.json
```

This command does not require `DATABASE_URL`. It never prints the API key.

Example config format:

```json
{
  "sources": [
    {
      "name": "Example marketplace listing pages",
      "type": "firecrawl",
      "url": "https://example.com/cars",
      "limit": 10,
      "document_type": "listing_snapshot",
      "crawl_depth": 1
    },
    {
      "name": "Local fixture documents",
      "type": "local_fixture",
      "path": "data/fixtures/ingestion",
      "limit": 3
    }
  ]
}
```

Supported source types:

- `firecrawl`: requires `name`, `url`, and `limit`; optional `document_type` defaults to `vehicle_profile`; optional `crawl_depth` defaults to `1`.
- `local_fixture`: requires `name`, `path`, and `limit`; included so source files can describe local and future external ingestion together.

Validation rules:

- `url` must be an `http` or `https` URL for `firecrawl` sources.
- `limit` must be between `1` and `100`.
- `crawl_depth` must be between `0` and `3`.
- `document_type` must match the existing `documents.document_type` values.

## Deduplication

The pipeline computes a SHA-256 `content_hash` after normalizing line endings. The hash is stored in `documents.metadata.content_hash`.

Document handling is conservative:

- same `source_id` and same `content_hash`: skip;
- same `source_id` and same `metadata.local_path` but changed content: update the document row;
- otherwise: insert a new document row.

The schema is not changed for this MVP pipeline.

## Read API

Ingested documents can be inspected through the backend read-only API:

```text
GET /documents
GET /documents/{document_id}
```

`GET /documents` supports filters for `source_id`, `vehicle_id`, `listing_id`, exact `document_type`, case-insensitive contains query `q`, `limit` up to `100`, and zero-based `offset`.

The API returns stored content and metadata, including `content_hash`, `local_path`, `proposed_vehicle`, `proposed_listing`, and `unparsed_fields`. It does not expose embeddings and does not write proposed values into `vehicles` or `listings`.

## Normalization

`normalize_vehicle_document` extracts only explicit labeled fields such as:

- `Make`
- `Model`
- `Year`
- `Price EUR`
- `Mileage km`
- `Fuel type`
- `Condition`
- `Location region`

Recognized values are stored as proposals in document metadata:

- `metadata.proposed_vehicle`
- `metadata.proposed_listing`

Uncertain or unparsed fields remain in `metadata.unparsed_fields`. The pipeline does not create or overwrite `vehicles`, `vehicle_specs`, or `listings`.

## Limits

- Firecrawl planner is dry-run only; no Firecrawl calls.
- No external HTTP calls.
- No embeddings.
- No LLM parsing.
- No automatic vehicle/listing writes beyond `documents`.
- Fixture values are synthetic and not authoritative.

To activate real Firecrawl ingestion later, add an HTTP client boundary that calls Firecrawl explicitly, convert crawl results into `LocalDocument`-compatible normalized documents, persist through the existing `documents` path, and add integration tests that mock the Firecrawl API. Do not enable automatic crawling from app startup or CI.
