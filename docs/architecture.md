# Drivewise Architecture

## Purpose

Drivewise helps users compare and evaluate vehicles before purchase. This MVP includes local app scaffolding, seed data, read-only vehicle/listing/document APIs, vehicle input resolution, document search with default text mode and explicit fake-vector dev mode, local fixture ingestion, deterministic Advisor v2 recommendations over reviewed exact-variant catalog offers with metric-level provenance, and a deterministic model analysis flow.

## Monorepo Layout

```text
apps/
  api/   FastAPI backend
  web/   TanStack Start frontend
docs/    architecture and project notes
```

## Frontend

`apps/web` uses TanStack Start with React and Vite. Bun is the frontend package manager. The current UI includes the `Drivewise MVP` home route, vehicle, listing, document explorer, document detail, document search, advisor, and model analysis routes:

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
/model-analysis
```

The frontend uses TanStack Router `Link` for internal navigation. The `/vehicles`, `/listings`, and `/documents` routes validate supported URL search parameters, derive loader dependencies from the normalized filters, and load matching collection data through route loaders. Server rendering and hydration therefore share the same filtered payload, while deep links and browser back/forward navigation preserve form and result state. Unknown or invalid search values are discarded before API calls. Shared pending and error boundaries handle loader navigation failures. Runtime API calls go through `apps/web/src/api/drivewise.ts`. Mock fallback is explicit and only activates when `VITE_USE_MOCK_API=true`; by default API failures are surfaced instead of hidden.

The vehicle, listing, and document detail routes also load their records through
route loaders. Direct detail URLs therefore render from the same loader payload
on the server and client, and reuse the shared pending and retryable error UI.
Missing detail records map API `404` responses to the router's not-found page.

## Backend

`apps/api` uses FastAPI. Implemented runtime endpoint groups are:

```text
GET /health
GET /ready
GET /vehicles
GET /vehicles/{vehicle_id}
POST /vehicles/resolve
GET /listings
GET /listings/{listing_id}
GET /documents
GET /documents/{document_id}
POST /search/documents
POST /advisor/recommendations
POST /advisor/model-analysis
```

`/health` returns a small JSON payload for cheap local health checks. `/ready` verifies PostgreSQL with a simple query and is the endpoint to use when a process must only receive traffic after the DB is reachable.

Database-backed dependencies use a small local connection pool initialized and closed through FastAPI lifespan. Settings are cached, CORS origins are configurable through `API_CORS_ORIGINS`, and local development defaults allow the TanStack app at `localhost:3000` and `127.0.0.1:3000`.

Vehicle resolution is deterministic and market-scoped. It normalizes free-text descriptions, ranks canonical vehicle/spec candidates by explicit make, model, year, trim, fuel, and body-style evidence, and reports matched, ambiguous, or no-match outcomes without writing to the database.

Document search is read-only and defaults to deterministic `text_only` scoring. It also supports explicit `vector_fake` dev/test mode, which embeds the query with the local `FakeEmbeddingProvider` and searches only documents that already have stored fake pgvector embeddings. Search responses never expose `embedding` or `embedding_model`. The Advisor v2 recommendations endpoint is independent of document search: it filters reviewed, fresh, exact Italian offer/spec pairs, produces transparent component scores and provenance, groups new and used results, and persists the versioned run and item breakdowns.

`POST /advisor/model-analysis` is a non-persisted flow for a model the user has already chosen. It can start from a free-text query resolved through the vehicle resolver or a canonical vehicle reference, then returns a result-contract shape with verdict, price assessment, estimated costs, red flags, checklist, confidence, assumptions, warnings, missing data, and next actions.

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
- Non-deterministic advisor/model-analysis logic
- Authentication
- Deployment configuration
