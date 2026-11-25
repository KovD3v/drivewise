# Drivewise Architecture

## Purpose

Drivewise helps users compare and evaluate vehicles before purchase. The build is API-first: the Decision Hub site calls a FastAPI backend that owns the catalogue, the persisted Guided Decision flow, deterministic Advisor v3 ranking over reviewed exact-variant offers and list prices with metric-level provenance, and a deterministic model analysis flow. Both run as one Vercel project (see "Deployment"). Development-only routes (listings, documents, search, vehicle resolution, raw recommendations) stay in the code behind `ENABLE_INTERNAL_ROUTES`.

## Monorepo Layout

```text
apps/
  api/   FastAPI backend
  web/   TanStack Start frontend
docs/    architecture and project notes
```

## Frontend

`apps/web` uses TanStack Start with React and Vite. Bun is the frontend package manager. The UI is the Decision Hub redesign (see [design-integration.md](design-integration.md)):

```text
/                      home
/app/start             Scelta Guidata (cars: Guided Decision API; motorcycles and scooters: catalogue)
/app/report            Riepilogo della scelta (Guided Decision ranking)
/app/vehicle/{id}      vehicle page
/app/compare           two vehicles side by side
/app/catalog?type=     motorcycle and scooter catalogue, without a score
/app/me                browser-local demo account
/contact /privacy /terms
```

The site is a client of the API (ADR-008): it computes no ranking, score, cost or
confidence and holds no vehicle data. Runtime API calls go through
`apps/web/src/api/drivewise.ts`, and an API failure is shown as an error, never
replaced by local data.

## Backend

`apps/api` uses FastAPI. The public endpoints, always served, are:

```text
GET  /health
GET  /ready
GET  /version
GET  /vehicles
GET  /vehicles/{vehicle_id}
GET  /vehicles/{vehicle_id}/facts
POST /advisor/model-analysis
POST /guided-decisions
POST /guided-decisions/{decision_id}/turns
GET  /guided-decisions/{decision_id}
```

The internal endpoints are served only when `ENABLE_INTERNAL_ROUTES` is on:

```text
GET  /docs, /redoc, /openapi.json
GET  /listings, /listings/{listing_id}
GET  /documents, /documents/{document_id}
POST /search/documents
POST /vehicles/resolve
POST /advisor/recommendations
```

`ENABLE_INTERNAL_ROUTES` defaults to on when `APP_ENV` is `local` or `test` and
to off in every other environment; an explicit `true` or `false` overrides the
default. When it is off, the listings, documents and search routers are not
mounted, the docs and OpenAPI URLs are disabled, and `POST /vehicles/resolve`
and `POST /advisor/recommendations` return `404` through the
`require_internal_routes` dependency. `bun run gen:api-types` imports the app
with the default `APP_ENV=local`, so the generated web types still include the
internal routes.

`/health` returns a small JSON payload for cheap local health checks. `/ready` verifies PostgreSQL with a simple query and is the endpoint to use when a process must only receive traffic after the DB is reachable. `/version` reports `service`, `api_version`, `git_commit` (`VERCEL_GIT_COMMIT_SHA`), `scoring_version` and `schema_version`, the newest migration file shipped with the build. `/vehicles/{vehicle_id}/facts` returns the vehicle's current Catalog v2 facts with their provenance.

Database-backed dependencies use a connection pool initialized and closed through FastAPI lifespan; each request's connection commits before the response is sent, so a failed commit never reaches the client as a `2xx`. Settings are cached. CORS fails closed: with `APP_ENV=local` the API allows `localhost:3000` and `127.0.0.1:3000` plus `API_CORS_ORIGINS`; in every other environment it allows only `API_CORS_ORIGINS`, and no origin when that is empty. It allows `GET`, `POST` and `OPTIONS`, the `Content-Type` header and no credentials. Guided decision responses are sent `Cache-Control: private, no-store`; successful catalogue reads may be cached for 60 seconds.

Vehicle resolution is deterministic and market-scoped. It normalizes free-text descriptions, ranks canonical vehicle/spec candidates by explicit make, model, year, trim, fuel, and body-style evidence, and reports matched, ambiguous, or no-match outcomes without writing to the database.

Document search is read-only and defaults to deterministic `text_only` scoring. It also supports explicit `vector_fake` dev/test mode, which embeds the query with the local `FakeEmbeddingProvider` and searches only documents that already have stored fake pgvector embeddings. Search responses never expose `embedding` or `embedding_model`. The Advisor v3 recommendations endpoint is independent of document search: it filters reviewed, fresh, exact Italian offer/spec pairs, evaluates constraints and versioned modules, produces the 65/35 decision score with component evidence and provenance, groups new and used results, and persists the versioned run and item breakdowns.

`POST /advisor/model-analysis` is a non-persisted flow for a model the user has already chosen. It can start from a free-text query resolved through the vehicle resolver or a canonical vehicle reference, then returns a result-contract shape with verdict, price assessment, estimated costs, red flags, checklist, confidence, assumptions, warnings, missing data, and next actions.

The Guided Decision API is a persisted, versioned state layer over the existing
deterministic Advisor v3. Each turn returns typed profile facts with confidence,
source, confirmation state, completion, engine confidence, missing information,
the next highest-impact question, and an optional Advisor v3 preview. The v1
wire contract is documented in `docs/guided-decision-contract.md`. Its current
Italian interpreter is deliberately conservative and isolated from scoring so
an LLM-backed interpreter can replace it without moving deterministic ranking
or constraints into the model. `GET /guided-decisions/{decision_id}` rebuilds
the ranking from the stored profile on every read, so a reopened report follows
the current catalogue and source permissions. A decision accepts at most 40
turns (`409 max_turns_reached`).

Advisor v3 is the only ranking runtime. TCO uses the versioned `tco-v1`
estimator today. Reliability, known issues, official recalls, Vehicle DNA, and
valuation have explicit adapters and documented input contracts, but no live
provider is claimed until its exact applicability, evidence, status, and
version requirements are met. See `docs/advisor-v3.md`.

## Data

The database is Neon PostgreSQL. [The data model page](data-model.md) describes every table and view. The schema lives in `apps/api/migrations`, uses Italian/European market assumptions for vehicle prices and specs, and enables the `vector` extension for pgvector-compatible embeddings storage.

Initial cache storage is planned in PostgreSQL. Redis is represented only by environment placeholders so a future task can add it without changing configuration conventions.

## Data Collection

The accepted change to vehicle identity and to the shape of catalogue facts
(ADR-020) is not built yet. It is in
[the identity and facts design](catalog-identity-and-facts-design.md).
[Catalog v2](catalog-v2.md) is implemented end to end: append-only evidence
storage (`0008`), reviewed publication into the read views (`0009`), two-wheel
metrics (`0010`), the list-price metric and read view (`0011`, `0012`),
plug-in hybrid fuel names (`0013`), body-style provenance (`0014`) and a single
`LATERAL` pivot of the read views that projects v2 dimensions, power and
provenance into Advisor v3 (`0015`). `0016` hardens it: `TRUNCATE` is rejected
like any other change to the append-only evidence tables, snapshot URLs must be
`https://`, decision validity dates must be ISO dates, and only a `human` or
`rule` decision makes a fact eligible for ranking. The migration runner holds an advisory
lock, so two concurrent runs cannot apply the same file twice.

Seed data comes from SQL migrations. Local fixture ingestion reads synthetic `.md`, `.txt`, and `.json` files from `data/fixtures/ingestion` and writes normalized content into `documents` only.

The legacy Firecrawl planner remains a dry run. `python apps/api/scripts/plan_firecrawl.py --sources data/sources.example.json` validates source names, types, URLs, limits, and API-key presence without HTTP requests or database writes.

The separate [manufacturer collection runner](scraping.md) implements on-demand
OpenRouter tool calling with Tinyfish Search/Fetch by default, optional Firecrawl
acquisition (`--provider firecrawl`), separately enabled Tinyfish Agent navigation
(`--tinyfish-agent`), and catalog v2 output.
Only its explicit `--run` mode contacts providers; application startup and the
legacy planner do not start collection.

Embeddings have a dry-run planner and a fake-provider write path. `python apps/api/scripts/plan_embeddings.py` reads documents missing embeddings from the configured database and prints a batch plan without provider calls or database writes. `python apps/api/scripts/embed_documents.py --provider fake --write` can write deterministic local `1536`-dimension fake vectors into `documents.embedding` for development; `POST /search/documents` can query them only when `mode` is explicitly `vector_fake`. No real provider SDKs or external calls are configured.

## Deployment

The root [`vercel.json`](../vercel.json) defines one Vercel project with two
services in region `fra1`: `web` (`apps/web`, TanStack Start) and `api`
(`apps/api`, FastAPI `app.main:app`). Rewrites send `/api/*` to the API and
everything else to the site, so the browser stays on one origin and the
production bundle calls `/api`. The `web` service receives the API's address as
`API_INTERNAL_URL` for server rendering, and the API runs with
`API_ROOT_PATH=/api`. Each service sets `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` and
a `Permissions-Policy` that denies camera, microphone and geolocation.

CI (`.github/workflows/ci.yml`) runs with `contents: read`, pins every action to
a commit SHA, and adds a blocking gitleaks scan and a reporting dependency audit
to the backend and frontend checks.

## Deferred Work

- Real Firecrawl crawling and live open-data or scraping runs (each needs its
  open findings closed first; see `CURRENT_STATUS.md`)
- Real external embedding providers
- Production hybrid/vector search
- Non-deterministic advisor/model-analysis logic
- Production LLM-backed guided-decision interpretation
- Authentication and real accounts (the `/app/me` account is browser-local)
- Retention limits for anonymous guided decisions and read-only share links
