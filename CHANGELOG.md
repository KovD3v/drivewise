# Changelog

All notable changes to Drivewise are documented in this file.

The format is based on
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Drivewise has no
versioned release yet, so every change after the `mvp-local-rag-v0` tag is under
Unreleased. The first versioned release will follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries up to 2026-11-25 were written from the Git history and the merged pull
requests. Each entry names its pull request, or its commit date when the change
went to `main` without one.

## [Unreleased]

### Added

- ADR-019, ADR-020, and the identity and facts design. A vehicle becomes one
  generation of one model in one market. A fact belongs to a generation or to a
  variant, and its value is a number or a code. The design is accepted and not
  built yet. ([#24])
- This changelog. ([#24])
- A daily workflow that deletes Guided Decision sessions older than 30 days.
  ([#23])
- A secret scan with gitleaks and a dependency audit in CI. ([#23])
- An open-data catalogue builder, `build_open_data_catalog.py`. It reads EEA CO2
  data, RDW open data, and MotoSpecDB, and writes a Catalog v2 bundle with a gap
  register. ([#22])
- A list-price fallback in Advisor v3. A model with no offer is ranked at its
  list price. ([#22])
- Motorcycles and scooters in the read catalogue, with
  `GET /vehicles?vehicle_type=` and two-wheel measurements. Every decision flow
  stays car-only. ([#19])
- `GET /version`, which reports the build, the scoring version, and the schema
  version. ([#18])
- The Decision Hub design in the web app: homepage, guided choice, report,
  vehicle page, comparison, My DriveWise, and the legal and contact pages.
  ([#11], [#21])
- Web types generated from the API's OpenAPI schema with
  `bun run gen:api-types`. ([#16])
- An on-demand collection pipeline for manufacturer documents,
  `scrape_catalog.py`. An OpenRouter agent finds and reads documents through
  Tinyfish, or through Firecrawl on request. Jobs resume from checkpoints, and
  each quoted value is checked against its document. ([#14])
- Catalog v2 publication: commands that check, stage, and publish a reviewed
  bundle, `GET /vehicles/{id}/facts`, and read views that admit a fact to
  ranking only when its decision and its source permit it. ([#13])
- The Catalog v2 evidence contract and its append-only tables for sources,
  snapshots, observations, and decisions. ([#12])
- Advisor v3 and the Guided Decision API, with stored decisions, turns, and
  recommendation runs. ([#5])
- The project memory pages, Decision Engine v1.0 with its calibration reports,
  and a five-vehicle development dataset. ([#4])
- `catalog_status.py`, which reports how many catalogue entries can be ranked.
  (2026-07-31)
- The Model Analysis flow, `POST /advisor/model-analysis`. (2026-07-15)
- The vehicle resolver, `POST /vehicles/resolve`, which matches a free-text
  query to vehicles and variants. ([#1])

### Changed

- The first real dataset has no fixed number of cars. ADR-015 and ADR-017 no
  longer say "twelve". ([#24])
- `docs/data-model.md` describes the schema after migration `0016`.
  `docs/f1-twelve-cars-curation.md` is now `docs/first-cars-curation.md`.
  ([#24])
- The API commits a transaction before it answers `2xx`, and the connection
  pool times out and retries dead connections. ([#23])
- The Catalog v2 read views supply dimensions, power, and provenance to
  Advisor v3. The Catalog v1 importer writes only in the `local` and `test`
  environments. ([#23])
- The web app shows only what the API returns. It no longer keeps its own copy
  of vehicles, scores, and confidence. ([#22])
- One Vercel project in `fra1` serves the site and the API from one domain.
  `/api/*` goes to FastAPI, so the browser needs no CORS. ([#17])
- The API runs on Vercel in Frankfurt, next to the Neon database. ([#16])
- Vehicle identity accepts overlapping generations and unknown years and
  trims. ([#13])
- Advisor v3 is the only ranking runtime. It replaces Decision Engine v1 and
  Advisor v2. ([#5])
- The web app loads collections through route loaders and keeps collection
  filters in the URL. (2026-07-15)
- The product roadmap is one document. ([#2])

### Removed

- Seven superseded documents: `TOMMASO_BACKLOG.md`, `TOMMASO_TASKS.md`,
  `DECISION_ENGINE_INTEGRATION.md`, `data-architecture-review.md`, the
  `2026-08-12_ENGINE_V1.md` snapshot, and the Advisor v3 plan and spec under
  `docs/superpowers/`. ([#24])
- The web app's mock data: 30 vehicles with hand-written scores, the mock API
  switch, and the two-wheel questionnaire behind fixed scores. ([#22])
- The uploaded Decision Hub archive. ([#11])
- The standalone Decision Engine v1 runtime. ([#5])
- Obsolete plan documents. ([#2])

### Fixed

- The guided car flow ended with no recommendation, and motorcycles and
  scooters showed scores that no engine had computed. ([#22])
- The web app built on Vercel but answered `404` on every route. ([#17])
- Document and listing detail routes no longer depend on the collection
  layouts. (2026-05-14)

### Security

- A decision signed only by an agent no longer makes a fact eligible for
  ranking. A person or a rule must sign it first. ([#23])
- `TRUNCATE` can no longer bypass the append-only evidence triggers, and
  snapshot URLs must be HTTPS. ([#23])
- Internal routes are off outside `local` and `test` unless
  `ENABLE_INTERNAL_ROUTES` is set. They are `/docs`, `/redoc`, `/openapi.json`,
  `/listings*`, `/documents*`, `POST /search/documents`,
  `POST /vehicles/resolve`, and `POST /advisor/recommendations`. ([#23])
- CORS is closed outside `local`, each Vercel service sends security headers,
  and CI actions are pinned to commit SHAs. ([#23])
- TanStack Start is updated past CVE-2026-102989. ([#15])

## [mvp-local-rag-v0] - 2026-05-14

### Added

- Project tooling and the environment contract in `.env.example`.
- The FastAPI service with runtime configuration, `GET /health`, `GET /ready`,
  and schema migrations.
- APIs for vehicles, listings, and documents.
- Local document ingestion and a Firecrawl planning command.
- Document search in two modes: text only, and vector search over fake
  embeddings.
- Embedding planning and a fake embedding provider.
- A deterministic advisor that cites document evidence.
- The Drivewise MVP web app.
- Operations documentation and a CI workflow.

[Unreleased]: https://github.com/KovD3v/drivewise/compare/mvp-local-rag-v0...HEAD
[mvp-local-rag-v0]: https://github.com/KovD3v/drivewise/releases/tag/mvp-local-rag-v0
[#1]: https://github.com/KovD3v/drivewise/pull/1
[#2]: https://github.com/KovD3v/drivewise/pull/2
[#4]: https://github.com/KovD3v/drivewise/pull/4
[#5]: https://github.com/KovD3v/drivewise/pull/5
[#11]: https://github.com/KovD3v/drivewise/pull/11
[#12]: https://github.com/KovD3v/drivewise/pull/12
[#13]: https://github.com/KovD3v/drivewise/pull/13
[#14]: https://github.com/KovD3v/drivewise/pull/14
[#15]: https://github.com/KovD3v/drivewise/pull/15
[#16]: https://github.com/KovD3v/drivewise/pull/16
[#17]: https://github.com/KovD3v/drivewise/pull/17
[#18]: https://github.com/KovD3v/drivewise/pull/18
[#19]: https://github.com/KovD3v/drivewise/pull/19
[#21]: https://github.com/KovD3v/drivewise/pull/21
[#22]: https://github.com/KovD3v/drivewise/pull/22
[#23]: https://github.com/KovD3v/drivewise/pull/23
[#24]: https://github.com/KovD3v/drivewise/pull/24
