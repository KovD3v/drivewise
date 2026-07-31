# Drivewise

Drivewise is an MVP for a vehicle purchase assistant.

The initial product wedge and private-beta gates are defined in
[`docs/product-beta.md`](docs/product-beta.md).

## Stack

- Frontend: TanStack Start
- Backend: FastAPI / Python
- Database: Neon PostgreSQL
- Vector search: pgvector on Neon
- Data collection: public sources, Hugging Face datasets, curated internal dataset, and future Firecrawl integration
- Cache: PostgreSQL first, Redis-ready later

## Prerequisites

- Node.js 20+
- Bun 1.3+
- Python 3.11+

## Local Setup

Copy the example environment file and fill local values as needed:

```bash
cp .env.example .env
```

The frontend reads `VITE_API_BASE_URL` and falls back to `http://127.0.0.1:8000` when it is not set. Mock API fallback is disabled by default; set `VITE_USE_MOCK_API=true` only when you intentionally want the browser to use local mock data after an API connection failure.

Install frontend dependencies:

```bash
bun install
```

Create a Python virtual environment and install the API:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e "apps/api[dev]"
```

## Neon PostgreSQL Setup

Create a Neon project from the [Neon Console](https://console.neon.tech/). In the project dashboard, use **Connect** to copy a PostgreSQL connection string for the branch, database, and role you want Drivewise to use.

Put the connection string in your local `.env` file:

```bash
DATABASE_URL="postgresql://[user]:[password]@[neon-host]/[database]?sslmode=require"
```

Keep `sslmode=require` in the URL. If Neon gives you a URL with extra parameters such as `channel_binding=require`, keep the whole value quoted in `.env`.

Apply database migrations and seed data to the database configured by `DATABASE_URL`:

```bash
. .venv/bin/activate
python apps/api/scripts/migrate.py
```

The migration script loads `.env`, refuses missing or placeholder `DATABASE_URL` values, reports already-applied migrations, and prints newly applied migrations.

Optionally ingest the local synthetic fixture documents:

```bash
. .venv/bin/activate
python apps/api/scripts/ingest_local.py --path data/fixtures/ingestion
```

The ingestion command writes only to `documents`, keeps proposed vehicle/listing values in metadata, and does not generate embeddings.

Run the backend:

```bash
. .venv/bin/activate
uvicorn app.main:app --reload --app-dir apps/api --host 127.0.0.1 --port 8000
```

API contract documentation is available in `docs/api-contract.md`.

Firecrawl ingestion is not active. To validate future source configuration without crawling or writing to the database:

```bash
python apps/api/scripts/plan_firecrawl.py --sources data/sources.example.json
```

`FIRECRAWL_API_KEY` is optional for planning and is never printed. The command only reports whether a key is configured.

Embedding planning is dry-run only. To inspect documents missing embeddings without calling external providers or writing to the database:

```bash
python apps/api/scripts/plan_embeddings.py --limit 20
```

Fake embeddings can be generated locally and written explicitly. The only available provider is deterministic and local; no OpenAI or other external provider is called:

```bash
python apps/api/scripts/embed_documents.py --provider fake --limit 20
python apps/api/scripts/embed_documents.py --provider fake --write --limit 20
```

The write command updates `documents.embedding` and `documents.embedding_model` only for rows missing embeddings. Add `--force` only when you intentionally want to overwrite existing embeddings.

After local ingestion and fake embedding writes, the search endpoint can run the
explicit dev/test vector mode without any external provider:

```bash
python apps/api/scripts/ingest_local.py --path data/fixtures/ingestion
python apps/api/scripts/embed_documents.py --provider fake --write --limit 20
curl -X POST http://127.0.0.1:8000/search/documents \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda","mode":"vector_fake","limit":10}'
```

Verify the API against the configured database:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/vehicles
curl -X POST http://127.0.0.1:8000/vehicles/resolve \
  -H "Content-Type: application/json" \
  -d '{"query":"Fiat Panda 1.0 FireFly hybrid 2024","market":"IT"}'
curl http://127.0.0.1:8000/listings
curl http://127.0.0.1:8000/documents
curl -X POST http://127.0.0.1:8000/search/documents \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda","limit":10}'
curl -X POST http://127.0.0.1:8000/search/documents \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda","mode":"vector_fake","limit":10}'
curl -X POST http://127.0.0.1:8000/vehicles/resolve \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda 1.0 firefly hybrid 2024","market":"IT"}'
curl -X POST http://127.0.0.1:8000/advisor/recommendations \
  -H "Content-Type: application/json" \
  -d '{"budget_max_eur":25000,"primary_use":"city","priorities":["price"]}'
curl -X POST http://127.0.0.1:8000/advisor/model-analysis \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda 1.0 firefly hybrid 2024","market":"IT","asking_price_eur":14500,"current_km":6400,"usage_profile":["city","mixed"],"analysis_scope":["price","maintenance","red_flags","tco"]}'
```

Run the frontend:

```bash
bun run dev:web
```

Open `http://localhost:3000`.

The `/search` page exposes the same backend search modes as
`POST /search/documents`: `text_only` by default and `vector_fake` for local
dev/test after fake embeddings have been written with `embed_documents.py`.
The `/model-analysis` page calls `POST /advisor/model-analysis` and shows the
result contract fields returned by the deterministic model analysis flow.

## Checks

Backend:

```bash
. .venv/bin/activate
pytest apps/api
ruff check apps/api
```

`/health` is a cheap process check. `/ready` verifies the configured database with `SELECT 1` and returns `503` when the database URL is missing, still placeholder-like, or unreachable.

To inspect the configured catalog without changing it, run:

```bash
uv run --project apps/api python apps/api/scripts/catalog_status.py
```

The report shows rankable listings, exclusion reasons, price coverage, and
body-style or fuel-type blind spots. Pass `--as-of <ISO8601>` to reproduce a
historical readiness check.

To run the optional database integration test, set `TEST_DATABASE_URL` to a disposable PostgreSQL database that supports pgvector, then run `pytest apps/api`. CI provides this with a local `pgvector/pgvector:pg16` service; no Neon database is required for CI.

Frontend:

```bash
bun run test:web
bun run typecheck:web
bun run build:web
```

## Scope

This repository currently contains the project base, backend health/readiness endpoints, read-only vehicle/listing/document APIs, deterministic vehicle resolution, document search with default `text_only` mode and explicit dev/test `vector_fake` mode, deterministic Advisor v2 recommendations over reviewed exact-variant catalog offers with metric-level provenance, a deterministic model analysis endpoint, frontend pages for `/vehicles`, `/listings`, `/documents`, `/search`, `/advisor`, and `/model-analysis`, the MVP database schema/seed, local fixture ingestion, a dry-run Firecrawl planning command, a dry-run embeddings planning command, and a fake-only embeddings write command for development. The vehicle, listing, and document collection routes validate filters from URL search parameters and load matching data through TanStack route loaders, making filtered views shareable and restorable through browser navigation. Their detail routes also load records through TanStack route loaders so direct detail URLs share a stable server/client payload and common pending/error states. Real Firecrawl crawling, real embedding providers, production hybrid/vector search, authentication, and Redis are intentionally deferred.
