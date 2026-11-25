# Drivewise

Drivewise is an MVP for a vehicle purchase assistant.

The initial product wedge and private-beta gates are defined in
[`docs/product-beta.md`](docs/product-beta.md).

## Stack

- Frontend: TanStack Start
- Backend: FastAPI / Python
- Database: Neon PostgreSQL
- Vector search: pgvector on Neon
- Data collection: trusted public sources, Tinyfish Search/Fetch, optional Firecrawl, and curated internal dataset
- Cache: PostgreSQL first, Redis-ready later

## Prerequisites

- Node.js 22 (pinned in `.nvmrc`; Vitest runs under Node, and Node 25 breaks the jsdom tests through its built-in `localStorage`, as found in PR #21)
- Bun 1.3+
- Python 3.12 (pinned in `apps/api/.python-version`)

## Local Setup

Copy the example environment file and fill local values as needed:

```bash
cp .env.example .env
```

The frontend reads `VITE_API_BASE_URL` and falls back to `http://127.0.0.1:8000` only when it is not set at build time. API failures are shown as errors; the site has no mock data.

### One origin (site and API under `/api`)

Build the site with `VITE_API_BASE_URL=/api` and run the API with `API_ROOT_PATH=/api`. Server rendering cannot fetch a relative URL, so the site server needs `API_INTERNAL_URL` (Vercel injects it; locally, for example, `http://127.0.0.1:8047/api`); without it a server render fails with an explicit error. Locally, `API_PROXY_TARGET=http://127.0.0.1:8047` at build or dev time makes the site forward `/api` to that API:

```bash
API_ROOT_PATH=/api uv run --project apps/api uvicorn app.main:app --app-dir apps/api --port 8047
cd apps/web
VITE_API_BASE_URL=/api API_PROXY_TARGET=http://127.0.0.1:8047 bun run build
API_INTERNAL_URL=http://127.0.0.1:8047/api PORT=3047 bun .output/server/index.mjs
```

`VITE_SYNTHETIC_DATA=true` at build time shows a demo notice on every page; use it with the synthetic demo catalogue (see `docs/catalog-v2.md`).

### Deployment (Vercel Services)

The unified build deploys as one Vercel project that builds both apps from the root
[`vercel.json`](vercel.json): the `web` service (`apps/web`, TanStack Start) and
the `api` service (`apps/api`, FastAPI `app.main:app`), in region `fra1`.
Requests to `/api/*` go to the API and everything else goes to the site, so the
browser stays on one origin. Vercel injects the API's address into the site as
`API_INTERNAL_URL` for server rendering. Both services send the same security
headers (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`,
`Permissions-Policy`).

The API needs `APP_ENV`, `DATABASE_URL` and `API_ROOT_PATH=/api` in the Vercel
environment. CORS fails closed: outside `APP_ENV=local` the API allows only the
origins listed in `API_CORS_ORIGINS`, and none when it is empty. Same-origin
traffic through `/api` needs no CORS entry.

### Public and internal API routes

`ENABLE_INTERNAL_ROUTES` decides whether the development and debug surface is
served. It defaults to on when `APP_ENV` is `local` or `test` and to off
everywhere else; set it to `true` or `false` to override. When it is off, these
return `404`: `/docs`, `/redoc`, `/openapi.json`, `/listings*`, `/documents*`,
`POST /search/documents`, `POST /vehicles/resolve` and
`POST /advisor/recommendations`. The public routes stay on:
`/health`, `/ready`, `/version`, `GET /vehicles`, `GET /vehicles/{id}`,
`GET /vehicles/{id}/facts`, `POST /advisor/model-analysis` and the
`/guided-decisions` routes.

`GET /version` reports the build: `service`, `api_version`, `git_commit` (from
`VERCEL_GIT_COMMIT_SHA`), `scoring_version` and `schema_version`.
`schema_version` is the newest migration file shipped with the build, not a
read of the database, so it does not show which migrations the database has
applied.

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

The legacy Firecrawl planner validates source configuration without crawling or writing to the database:

```bash
python apps/api/scripts/plan_firecrawl.py --sources data/sources.example.json
```

`FIRECRAWL_API_KEY` is optional for planning and is never printed. The command only reports whether a key is configured.

The [open-data import](docs/open-data-import.md) builds catalog v2 bundles from two
public registries (EEA and RDW) with no key and no cost. What it cannot fill is
listed in [docs/open-data-gaps.md](docs/open-data-gaps.md).

The [manufacturer collection agent](docs/scraping.md) uses OpenRouter with Tinyfish
Search/Fetch by default. Firecrawl is an optional acquisition alternative, and
Tinyfish Agent navigation can be enabled separately. It produces catalog v2 bundles
in an explicitly started job. Preview its scope without keys or network access:

```bash
uv run --frozen --project apps/api python apps/api/scripts/scrape_catalog.py --config data/scraping.example.json
```

Add `--run --run-dir data/private/catalog/yaris-pilot` only when keys and an
OpenRouter model are configured. Collection resumes from local checkpoints;
publication remains a separate command.

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

Verify the public API against the configured database:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/version
curl http://127.0.0.1:8000/vehicles
curl -X POST http://127.0.0.1:8000/advisor/model-analysis \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda 1.0 firefly hybrid 2024","market":"IT","asking_price_eur":14500,"current_km":6400,"usage_profile":["city","mixed"],"analysis_scope":["price","maintenance","red_flags","tco"]}'
```

The internal routes answer only when `ENABLE_INTERNAL_ROUTES` is on, which is
the default with `APP_ENV=local` or `test` (see "Public and internal API routes"):

```bash
curl http://127.0.0.1:8000/listings
curl http://127.0.0.1:8000/documents
curl -X POST http://127.0.0.1:8000/vehicles/resolve \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda 1.0 firefly hybrid 2024","market":"IT"}'
curl -X POST http://127.0.0.1:8000/search/documents \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda","limit":10}'
curl -X POST http://127.0.0.1:8000/search/documents \
  -H "Content-Type: application/json" \
  -d '{"query":"fiat panda","mode":"vector_fake","limit":10}'
curl -X POST http://127.0.0.1:8000/advisor/recommendations \
  -H "Content-Type: application/json" \
  -d '{"budget_max_eur":25000,"primary_use":"city","priorities":["price"]}'
```

Run the frontend:

```bash
bun run dev:web
```

Open `http://localhost:3000`. The site is the Decision Hub (see
[`docs/design-integration.md`](docs/design-integration.md)); its routes are:

| Route | Page |
| --- | --- |
| `/` | Home and the first free-text request |
| `/app/start` | Guided choice: cars through the Guided Decision API, motorcycles and scooters through the catalogue |
| `/app/report?s=<decision id>` | Decision report, loaded from `GET /guided-decisions/{id}` |
| `/app/vehicle/$id` | Vehicle page (`?spec=` keeps the chosen variant) |
| `/app/compare?vehicle=&with=` | Two vehicles of one type side by side (`spec` and `withSpec` keep the variants) |
| `/app/catalog?type=` | Motorcycle and scooter catalogue, without a score |
| `/app/me` | Browser-local demo account |
| `/contact`, `/privacy`, `/terms` | Contact (simulated, nothing is sent) and legal pages |

The earlier MVP pages (`/vehicles`, `/listings`, `/documents`, `/search`,
`/advisor`, `/model-analysis`) were removed; their API routes remain for
development as listed above.

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

To run the optional database integration test, set `TEST_DATABASE_URL` to a disposable PostgreSQL database that supports pgvector, then run `pytest apps/api`. CI provides this with a local `pgvector/pgvector:pg18` service; no Neon database is required for CI.

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs with read-only
repository permissions and pins every third-party action to a commit SHA. Besides
the backend and frontend checks it runs two more jobs:

- **Secret scan:** gitleaks 8.30.1, checksum-verified, with
  [`.gitleaks.toml`](.gitleaks.toml), over the working tree and over the commits
  the pull request or push adds. It blocks the merge on a finding.
- **Dependency audit:** `bun audit --audit-level=high` on `bun.lock` and
  `pip-audit` on the `apps/api/uv.lock` export. Both report in the job summary
  without failing CI until the advisories already in the lockfiles are fixed;
  then remove `continue-on-error` so new advisories block.

Frontend:

```bash
bun run test:web
bun run typecheck:web
bun run build:web
```

## Scope

This repository holds the Decision Hub site and the API behind it. The site is
an API client (ADR-008): it computes no ranking, score or cost and holds no
vehicle data. The API provides health, readiness and `/version`; the vehicle
catalogue with Catalog v2 facts and provenance; the persisted Guided Decision
flow, whose report is recomputed against the current catalogue on every read;
deterministic Advisor v3 ranking over reviewed exact-variant offers and list
prices; and the deterministic model analysis. Catalog v2 evidence storage,
publication and read views come from migrations `0008` to `0015` (see
[`docs/catalog-v2.md`](docs/catalog-v2.md)). The data tools are offline or
explicitly started: local fixture ingestion, the open-data catalogue builder,
the manufacturer collection agent, a dry-run Firecrawl planner and fake-only
embeddings. Real embedding providers, production vector search, authentication
and Redis are deferred. The current state and the next gates are in
[`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).
