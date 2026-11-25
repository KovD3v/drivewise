# DriveWise project context

_Last updated: 2026-11-25_

## Product vision
DriveWise is a vehicle Decision Intelligence product. It helps a person choose the right vehicle for their real context rather than returning a generic recommendation or a list of listings. The initial MVP focuses on cars, with the architecture designed to extend later to motorcycles and scooters.

The core product promise is: **DriveWise does not decide by conversational intuition alone. It builds a structured Decision Profile, evaluates vehicles through deterministic Advisor v3, exposes trade-offs and confidence, and uses AI primarily to interpret requests and explain results.**

## Experience
The public Landing is intentionally separate from the Web App. The Landing explains why DriveWise is different from a generic AI. The Web App starts at `/app/start` and implements an adaptive guided choice. It must never feel like a generic chatbot or a fixed questionnaire.

The user can write freely. DriveWise extracts structured facts, updates `DriveWise conosce già...`, asks one high-value question at a time, shows Profile Completion and Decision Confidence separately, and eventually generates a Decision Report. Vehicle detail pages explain why a vehicle fits the user and include Vehicle DNA, known issues, recalls, maintenance, TCO, depreciation, real consumption, trade-offs, alternatives and Garage Fit.

## Advisor v3
The ranking runtime is deterministic Python code in the API. Its composition is:
- 65% Structural Fit
- 35% Preference Fit

Structural Fit includes Economics, Practicality, Reliability & Safety, Driving, Technology, Powertrain Fit, hard/soft constraints, TCO, Garage Fit and quality penalties.

Preference Fit compares the vehicle directly with the user's ranked top-3 priorities (50% / 30% / 20%).

The LLM does **not** calculate the ranking. It may interpret free text and explain structured outputs.

## Confidence model
Decision Score and Decision Confidence are different concepts.
- Decision Score: suitability of a specific vehicle for a specific user.
- Decision Confidence: confidence in the recommendation based on profile completeness, vehicle data quality and ranking stability.
- Data Quality uses source reliability, freshness, verification and per-domain confidence.

## Data
The catalogue lives in PostgreSQL (Neon in production). Catalog v2 stores sourced evidence and reviewed decisions and publishes them to the read views Advisor v3 uses (migrations `0008`–`0016`). No database holds reviewed real cars yet: the seed rows of migrations `0003`–`0004` and the synthetic demo catalogue (`data/fixtures/catalog/catalog-v2.demo.synthetic.json`, shown with a demo notice when the site is built with `VITE_SYNTHETIC_DATA=true`) are development material. Under ADR-011 they must not be presented as production-grade automotive truth. The first real data is the 12-car curation of ADR-017 ([`f1-twelve-cars-curation.md`](f1-twelve-cars-curation.md)).

## Architecture direction
The Decision Hub site (`apps/web`, TanStack Start, design imported from the Lovable exports) is the presentation layer. `apps/api/app/services/advisor/` is the source of truth for ranking. The integration is live:

`Decision Hub site -> /api (same origin) -> FastAPI -> Advisor v3 -> PostgreSQL catalogue`

Site and API deploy together as one Vercel project (`vercel.json`). Do not duplicate the scoring algorithm in TypeScript. The frontend consumes API payloads and types generated from the API's OpenAPI schema.

## MVP user journey
1. Landing
2. User enters an initial request or starts the guided flow
3. `/app/start` builds Decision Profile
4. extracted facts + adaptive next question
5. Profile Completion / Decision Confidence update
6. preliminary ranking appears when useful
7. analysis state
8. Decision Report
9. Vehicle detail
10. contextual questions / compare later

## Key product principles
- One question at a time.
- Never ask what has already been inferred with sufficient confidence.
- Explain why a question matters when useful.
- Hard constraints exclude; preferences influence score.
- No vehicle has an absolute Decision Score independent of the user.
- Every recommendation must expose strengths and compromises.
- Source quality and freshness matter.
- Do not hide uncertainty.
- Garage compatibility is a first-class decision factor when the user supplies dimensions.
- UI should transform data into decisions, not dump tables.

## Current product state
- Build: API-first and unified on `main` since PR #22, hardened by the Architectural Council decisions A–F (see [`CURRENT_STATUS.md`](CURRENT_STATUS.md)).
- Landing: November 2026 Lovable design, merged onto the API-backed site.
- `/app/start`: live Guided Decision against the API for cars; motorcycles and scooters open the catalogue.
- Decision Report: `/app/report?s=<decision id>` loads from the API and recomputes the ranking on every read.
- Vehicle detail and comparison: API data, with `?spec=` keeping the chosen variant; Garage Fit included.
- Catalogue: seed and synthetic demo data only; no reviewed real cars yet.
- Advisor v3: the only ranking runtime, in the API and the Guided Decision.
- Next milestone: curate, review and publish the first 12 real cars (ADR-017, [`f1-twelve-cars-curation.md`](f1-twelve-cars-curation.md)), after the production ops gates in `CURRENT_STATUS.md`.

## Ownership split
- Product/UX/Decision model: Andrea.
- Backend/data/API implementation: Tommaso.

## How to resume in a new AI session
Read, in order:
1. `docs/PROJECT_CONTEXT.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/snapshots/2026-11-24_PR_PROCESS_REVIEW_SECURITY_ROADMAP.md` (open findings and roadmap)
4. `docs/f1-twelve-cars-curation.md`
5. `docs/DECISIONS.md`
6. `docs/advisor-v3.md`
7. `docs/api-contract.md` and `docs/architecture.md`

Then continue from the first item under **Remaining pre-go-live gates** in `CURRENT_STATUS.md`. `docs/TOMMASO_TASKS.md` and `docs/TOMMASO_BACKLOG.md` are historical.
