# DriveWise — Backend Delivery Plan for Tommaso

_Owner: Tommaso — Backend / Data / API_
_Status: Ready to start_
_Priority: Critical for MVP_

## 1. Mission

The objective is not to design a second scoring system. The Decision Engine v1.0 in `decision_engine/` is the source implementation for MVP recommendation logic.

Tommaso's job is to turn the existing prototype assets into a reliable backend boundary that Lovable can consume.

The first successful milestone is a working vertical slice:

`Lovable /app/start → backend API → Decision Engine v1.0 → ranking JSON → Lovable Decision Report`

## 2. Non-negotiable architectural rules

1. **Do not copy scoring formulas into controllers or TypeScript.**
2. Keep the Decision Engine as a standalone Python domain module.
3. API/service code may map DTOs to `DecisionProfile`, invoke the engine, and map the result back to DTOs.
4. The LLM must not calculate the ranking.
5. Do not persist `Decision Score` as a permanent property of a vehicle. It is contextual to a decision session/profile.
6. `Decision Confidence` must remain separate from `Decision Score`.
7. Preserve explainability fields; do not reduce the engine output to only `vehicle_id + score`.
8. Backend must be testable without Lovable.

---

# Sprint A — Backend Foundation

## A1. Inspect current repository before coding

Review:
- existing backend/apps structure;
- `docs/api-contract.md`;
- `docs/architecture.md`;
- current data ingestion/catalog code;
- `decision_engine/README.md`;
- `docs/PROJECT_CONTEXT.md` and `docs/DECISIONS.md`.

Do not create duplicate services if equivalent code already exists.

**Deliverable:** short README/PR description explaining which existing modules are reused and which new modules are introduced.

## A2. FastAPI application boundary

Create or adapt a FastAPI application with versioned API prefix:

`/api/v1`

Minimum platform endpoints:
- `GET /api/v1/health`
- `GET /api/v1/version`

Health should confirm the API process is alive; version should return backend and Decision Engine versions.

**Acceptance:** service starts locally with one documented command and OpenAPI is reachable.

## A3. Dependency/config management

Define environments without committing secrets.

Expected configuration areas:
- environment name;
- allowed CORS origins;
- database URL if persistence is enabled;
- logging level;
- optional LLM credentials only when explanation service is implemented later.

Use `.env.example`; never commit real secrets.

## A4. CORS for Lovable

Configure CORS explicitly for the deployed Lovable frontend and local development.

Do not use unrestricted `*` in production configuration unless explicitly approved.

---

# Sprint B — Decision Engine Integration

## B1. Package/import the engine

Integrate `decision_engine/drivewise_engine` as an application dependency.

Preferred approaches:
- local package in monorepo with Python package metadata; or
- internal module dependency if backend is already Python monorepo.

Avoid copying individual engine files into multiple locations.

## B2. Preserve engine tests

Run the supplied engine regression tests before modifying anything.

At freeze time v1.0 had 11 passing tests. Backend changes must not alter scoring behavior unintentionally.

If a test requires adaptation because packaging changes, preserve its behavioral assertion.

## B3. Decision DTOs

Create typed request/response models matching the engine contract.

Minimum `DecisionProfileRequest` fields:
- `budget_max`
- `annual_km`
- `usage[]`
- `priorities[]`
- `vehicle_type`
- `category?`
- `category_is_hard_constraint`
- `new_or_used`
- `garage?`
- `automatic_required`
- `fuel_constraints[]`
- `children_count`
- `passengers_usual`

Garage object should use millimetres internally:
- `length_mm`
- `width_mm`
- `height_mm`
- `door_width_mm`
- `door_height_mm`

Validate ranges and reject impossible values with meaningful 4xx responses.

## B4. Decision endpoint — MVP priority

Implement:

`POST /api/v1/decisions`

Input: structured Decision Profile.

Flow:
1. validate request;
2. map DTO → `DecisionProfile`;
3. load eligible vehicle catalog;
4. call Decision Engine v1.0;
5. generate a decision/session id;
6. return ranking and excluded vehicles;
7. optionally persist the decision if persistence layer is ready.

Minimum response fields:
- `decision_id`
- `decision_confidence`
- `profile_completeness`
- `ranking[]`
- `excluded[]`

Each ranking item must preserve:
- `rank`
- `vehicle_id`
- `decision_score`
- `decision_confidence`
- `data_quality`
- `pillars`
- `strengths[]`
- `tradeoffs[]`
- `penalties`
- `explainability`

**Acceptance:** the family demo profile returns an ordered ranking and explainability without Lovable.

## B5. Retrieve decision

Implement:

`GET /api/v1/decisions/{decision_id}`

If persistence is not ready in the first slice, an in-memory adapter is acceptable only for local demo, behind a clearly marked repository interface. Do not hardwire in-memory storage into controllers.

## B6. Engine version in output

Include engine version in response metadata, e.g.:

```json
"meta": {
  "engine_version": "1.0",
  "data_version": "mvp-v0.2"
}
```

This will be important when ranking changes after future calibration.

---

# Sprint C — Vehicle Catalog APIs

## C1. Vehicle repository abstraction

Create a `VehicleRepository` interface/port.

Initial implementation may read the current JSON fixtures, but the Decision Service must not know whether vehicles come from JSON, PostgreSQL or another catalog store.

Suggested methods:
- `list(filters)`
- `get_by_id(vehicle_id)`
- `get_many(ids)`
- `get_active_for_decision(profile)`

## C2. List vehicles

Implement:

`GET /api/v1/vehicles`

Support basic filters needed by frontend/admin/debugging:
- brand;
- category;
- fuel;
- new/used when available;
- price min/max;
- limit/offset.

Do not try to build a complete marketplace search API in the MVP.

## C3. Vehicle detail

Implement:

`GET /api/v1/vehicles/{vehicle_id}`

Must return the fields required by the current Vehicle Page:
- identity/version;
- pricing;
- dimensions;
- powertrain;
- consumption/range;
- reliability;
- safety;
- Vehicle DNA;
- known issues;
- pre-purchase checks;
- recalls;
- maintenance;
- ownership costs;
- depreciation;
- strengths/trade-offs;
- alternatives.

Decision-specific fields such as score/confidence should not be returned as static vehicle attributes.

## C4. Decision-aware vehicle detail

For a vehicle opened from a report, prefer either:

`GET /api/v1/decisions/{decision_id}/vehicles/{vehicle_id}`

or an equivalent documented pattern.

This response combines static vehicle data with contextual values:
- Decision Score;
- Decision Confidence;
- personalized TCO;
- Garage Fit;
- personalized strengths/trade-offs;
- explainability.

This prevents the frontend from trying to reconstruct contextual scoring.

---

# Sprint D — Session / Guided Decision Flow

This can follow the first direct decision endpoint; do not block the initial vertical slice on conversational orchestration.

## D1. Session model

Create a Decision Session object containing at least:
- `session_id`
- current Decision Profile;
- confirmed fields;
- inferred fields/confidence where applicable;
- missing-information priorities;
- profile completeness;
- created/updated timestamps.

## D2. Start session

Implement:

`POST /api/v1/decision-sessions`

The initial frontend free-form query can eventually be parsed by an LLM/extraction service, but keep extraction separated from scoring.

Output should contain:
- current structured profile;
- extracted facts;
- next question;
- profile completion;
- preliminary confidence/ranking when threshold is reached.

## D3. Continue session

Implement:

`POST /api/v1/decision-sessions/{session_id}/answers`

The backend updates profile state and returns the next best question / preview ranking.

The API must support both:
- free-text answers;
- structured quick-choice responses.

## D4. Question selection

Do not hardcode a single fixed questionnaire sequence.

Use missing-information priority so the service can ask the most useful unresolved question and skip already known fields.

The frontend should receive a typed `nextQuestion`, e.g. `number`, `single_choice`, `multi_choice`, `ranking`, `boolean`, `dimensions`, `confirmation`.

---

# Sprint E — Garage Fit

## E1. Reuse engine logic

Do not implement a second Garage Fit formula in API code.

Expose the engine result with:
- fit score;
- status;
- margins in mm;
- vehicle dimensions used;
- garage dimensions used.

## E2. Contextual output

Backend output should make it possible for frontend to render:
- `fits_comfortably`
- `fits_tight`
- `fits_very_tight`
- `does_not_fit`
- `unknown`

The UI explanation can be generated from the deterministic margins.

---

# Sprint F — Dataset / Data Quality

## F1. Import the v0.2 fixtures

Use `dataset/mvp-v0.2` as a development fixture only.

Do not assume values are authoritative production data.

## F2. Validation

Validate catalog records before they become eligible for decisions.

Minimum validation:
- stable unique id;
- numeric values non-negative and plausible;
- normalized enums;
- required dimension fields;
- pricing currency;
- provenance metadata where available.

Invalid records should be reported, not silently accepted.

## F3. Provenance

Preserve or add metadata for important domains:
- source;
- confidence;
- updated_at;
- verified.

This is required by Decision Confidence/Data Quality.

## F4. Dataset versioning

Every decision response must be traceable to a dataset/catalog version.

Do not overwrite datasets without version identity.

## F5. Production data strategy

Before scaling beyond fixtures, produce a short technical proposal covering:
- sources/licensing;
- ingest frequency;
- normalization;
- deduplication/version matching;
- update strategy;
- recall refresh;
- known-issue evidence policy.

---

# Sprint G — Persistence

## G1. PostgreSQL-ready design

Even if JSON/in-memory is used in the first demo, structure repositories so PostgreSQL can replace the adapter.

Likely entities:
- vehicles / vehicle_versions;
- data provenance records;
- decision sessions;
- decision profiles;
- decision results/ranking snapshots;
- users later, not required to block anonymous MVP.

## G2. Reproducibility

A persisted decision should be reproducible by recording:
- engine version;
- data version;
- input profile snapshot;
- ranking snapshot;
- timestamp.

---

# Sprint H — Explainability / AI Integration

This is deliberately after deterministic API integration.

## H1. Explanation service

Create a service that receives the engine's structured explainability payload and produces Italian natural-language explanation.

The model may explain but not alter:
- rank;
- Decision Score;
- pillar scores;
- hard-filter decisions.

## H2. Safety against hallucinated automotive facts

The LLM prompt/context must be restricted to backend-provided structured data and approved sources. If data is absent, output should acknowledge it rather than invent a fact.

## H3. Contextual Q&A

`Ask DriveWise` on Vehicle Page should eventually call a contextual endpoint that receives vehicle id + optional decision id + user question.

Do not expose generic unrestricted chatbot behavior as the core product experience.

---

# Sprint I — Testing

## I1. Unit tests
Maintain Decision Engine tests.

## I2. API tests
At minimum test:
- valid decision request;
- invalid ranges;
- hard category constraint;
- fuel hard constraint;
- garage exclusion;
- unknown vehicle;
- unknown decision/session;
- deterministic repeatability for same engine/data/profile.

## I3. Golden fixtures
Create golden JSON fixtures for 3–5 known profiles so frontend and backend can verify contract stability.

## I4. Contract tests
Validate actual API responses against OpenAPI/Pydantic schema used by frontend.

## I5. Performance target for MVP
Decision calculation on the small catalog should feel immediate. Capture timings in logs and define a target before catalog scale-up. Do not prematurely optimize before measuring.

---

# Sprint L — Observability and Operational Basics

Implement structured logging including:
- request/correlation id;
- decision id/session id;
- engine version;
- dataset version;
- elapsed decision time;
- error class.

Never log secrets or unnecessary free-form user content containing personal data.

Add meaningful errors with stable error codes for frontend handling.

---

# Required API MVP — priority order

### P0
- `GET /api/v1/health`
- `GET /api/v1/version`
- `POST /api/v1/decisions`
- `GET /api/v1/vehicles/{id}`
- `GET /api/v1/decisions/{decision_id}` or equivalent persistence route

### P1
- `GET /api/v1/vehicles`
- decision-aware vehicle detail
- decision session start/continue

### P2
- AI explanation/Q&A
- auth/account persistence
- catalog administration endpoints

---

# First demo profile for acceptance

Use a profile equivalent to:

```json
{
  "budget_max": 35000,
  "annual_km": 22000,
  "usage": ["family", "city", "highway"],
  "priorities": ["reliability", "running_cost", "comfort"],
  "vehicle_type": "car",
  "children_count": 2,
  "passengers_usual": 4,
  "garage": {
    "length_mm": 5000,
    "width_mm": 2400,
    "height_mm": 2100,
    "door_width_mm": 2200,
    "door_height_mm": 2050
  }
}
```

The exact score may evolve only through an intentional engine version change. The response must preserve full ranking/explainability structure.

---

# Definition of Done — Tommaso MVP backend

Tommaso's backend phase is considered MVP-ready when:

- [ ] backend starts locally from documented instructions;
- [ ] FastAPI/OpenAPI available;
- [ ] Decision Engine v1.0 is imported, not reimplemented;
- [ ] engine regression tests pass;
- [ ] `POST /api/v1/decisions` executes real Python scoring;
- [ ] Decision Score/Confidence/explainability returned to client;
- [ ] vehicle detail is data-driven;
- [ ] contextual Decision Score is not stored as static vehicle rating;
- [ ] Garage Fit comes from engine/domain logic;
- [ ] source/data metadata survives catalog loading;
- [ ] errors are structured;
- [ ] Lovable CORS configured;
- [ ] frontend can complete one end-to-end journey using backend APIs;
- [ ] no production secrets are committed;
- [ ] engine version and dataset version are visible in decision output;
- [ ] API and local setup are documented in the repo.

## What Tommaso should NOT spend time on yet

- redesigning the Lovable UI;
- rebuilding the ranking algorithm;
- implementing a generic chatbot;
- complex authentication before anonymous MVP works;
- scaling infrastructure for millions of records before the data model is validated;
- adding many endpoints that the current user journey does not need.

The priority is a thin, reliable, testable vertical slice from the current Lovable experience to the frozen Decision Engine.
