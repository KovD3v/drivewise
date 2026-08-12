# DriveWise — Project Context

_Last updated: 2026-08-12_

## Product vision
DriveWise is a vehicle Decision Intelligence product. It helps a person choose the right vehicle for their real context rather than returning a generic recommendation or a list of listings. The initial MVP focuses on cars, with the architecture designed to extend later to motorcycles and scooters.

The core product promise is: **DriveWise does not decide by conversational intuition alone. It builds a structured Decision Profile, evaluates vehicles through a deterministic Decision Engine, exposes trade-offs and confidence, and uses AI primarily to interpret requests and explain results.**

## Experience
The public Landing is intentionally separate from the Web App. The Landing explains why DriveWise is different from a generic AI. The Web App starts at `/app/start` and implements an adaptive guided choice. It must never feel like a generic chatbot or a fixed questionnaire.

The user can write freely. DriveWise extracts structured facts, updates `DriveWise conosce già...`, asks one high-value question at a time, shows Profile Completion and Decision Confidence separately, and eventually generates a Decision Report. Vehicle detail pages explain why a vehicle fits the user and include Vehicle DNA, known issues, recalls, maintenance, TCO, depreciation, real consumption, trade-offs, alternatives and Garage Fit.

## Decision Engine v1.0
The MVP scoring engine is deterministic Python code. Frozen MVP composition:
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
The current dataset is synthetic/mock and exists to stabilize contracts and UI. It contains five differentiated vehicles and fields for technical data, Vehicle DNA, known issues, recalls, maintenance, TCO, depreciation, Garage Fit, strengths and trade-offs. It must not be presented as production-grade automotive truth.

## Architecture direction
Lovable/React is the presentation layer. Python remains the source of truth for the Decision Engine. The intended integration is:

`Lovable frontend -> REST API -> Python backend/FastAPI -> Decision Engine -> Dataset/DB`

Do not duplicate the scoring algorithm in TypeScript. The frontend consumes API payloads.

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
- Landing: mature MVP design.
- `/app/start`: implemented as Lovable mock flow and requires real API integration next.
- Decision Report: mock UI exists.
- Vehicle detail: rich UI exists, including Garage Fit redesign.
- Dataset v0.2: synthetic development dataset.
- Decision Engine v1.0: frozen MVP architecture and calibrated against 12 synthetic profiles.
- Backend/API integration: next major technical milestone.

## Ownership split
- Product/UX/Decision model: Andrea.
- Backend/data/API implementation: Tommaso.

## How to resume in a new AI session
Read, in order:
1. `docs/PROJECT_CONTEXT.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/DECISIONS.md`
4. `docs/TOMMASO_TASKS.md`
5. Decision Engine README/frozen package
6. `docs/api-contract.md` and `docs/architecture.md`

Then continue from the first item under **Next actions** in `CURRENT_STATUS.md`.
