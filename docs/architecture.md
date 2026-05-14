# Drivewise Architecture

## Purpose

Drivewise helps users compare and evaluate vehicles before purchase. This MVP includes local app scaffolding, seed data, read-only vehicle/listing/document APIs, document search with default text mode and explicit fake-vector dev mode, local fixture ingestion, and a deterministic advisor flow with document evidence.

## Monorepo Layout

```text
apps/
  api/   FastAPI backend
  web/   TanStack Start frontend
docs/    architecture and project notes
```

## Frontend

`apps/web` uses TanStack Start with React and Vite. Bun is the frontend package manager. The current UI includes the `Drivewise MVP` home route, vehicle, listing, document explorer, document detail, document search, and advisor routes:

```text
/
/vehicles
/vehicles/{vehicle_id}
/listings
/listings/{listing_id}
/documents
/documents/{document_id}
/search
/advisor
```

The frontend uses TanStack Router `Link` for internal navigation. Runtime API calls go through `apps/web/src/api/drivewise.ts`. Mock fallback is explicit and only activates when `VITE_USE_MOCK_API=true`; by default API failures are surfaced instead of hidden.

## Backend

`apps/api` uses FastAPI. Implemented runtime endpoint groups are:

```text
GET /health
GET /ready
GET /vehicles
GET /vehicles/{vehicle_id}
GET /listings
GET /listings/{listing_id}
GET /documents
GET /documents/{document_id}
POST /search/documents
POST /advisor/recommendations
```

`/health` returns a small JSON payload for cheap local health checks. `/ready` verifies PostgreSQL with a simple query and is the endpoint to use when a process must only receive traffic after the DB is reachable.

Database-backed dependencies use a small local connection pool initialized and closed through FastAPI lifespan. Settings are cached, CORS origins are configurable through `API_CORS_ORIGINS`, and local development defaults allow the TanStack app at `localhost:3000` and `127.0.0.1:3000`.

Document search is read-only and defaults to deterministic `text_only` scoring. It also supports explicit `vector_fake` dev/test mode, which embeds the query with the local `FakeEmbeddingProvider` and searches only documents that already have stored fake pgvector embeddings. Search responses never expose `embedding` or `embedding_model`. The advisor endpoint is deterministic, persists recommendation runs/items, and enriches response items with transient `document_evidence` from text-only document search. `document_evidence` is not stored in `recommendation_items` and does not affect advisor scoring or ranking.

## Data

The intended database is Neon PostgreSQL. The MVP schema lives in `apps/api/migrations`, uses Italian/European market assumptions for vehicle prices and specs, and enables the `vector` extension for pgvector-compatible embeddings storage.

Initial cache storage is planned in PostgreSQL. Redis is represented only by environment placeholders so a future task can add it without changing configuration conventions.

## Data Collection

Seed data comes from SQL migrations. Local fixture ingestion reads synthetic `.md`, `.txt`, and `.json` files from `data/fixtures/ingestion` and writes normalized content into `documents` only.

Firecrawl has a dry-run planner and source configuration shape, but no real crawler is active. `python apps/api/scripts/plan_firecrawl.py --sources data/sources.example.json` validates source names, types, URLs, limits, and API-key presence without HTTP requests or database writes.

Embeddings have a dry-run planner and a fake-provider write path. `python apps/api/scripts/plan_embeddings.py` reads documents missing embeddings from the configured database and prints a batch plan without provider calls or database writes. `python apps/api/scripts/embed_documents.py --provider fake --write` can write deterministic local `1536`-dimension fake vectors into `documents.embedding` for development; `POST /search/documents` can query them only when `mode` is explicitly `vector_fake`. No real provider SDKs or external calls are configured.

## Deferred Work

- Real Firecrawl crawling
- Real external embedding providers
- Production hybrid/vector search
- Non-deterministic advisor logic
- Authentication
- Deployment configuration
