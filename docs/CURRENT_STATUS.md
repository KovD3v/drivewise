# DriveWise current status

_Last updated: 2026-08-25_

## Overall phase

MVP implementation with the Advisor v3 runtime integrated in the API and
Guided Decision flow.

## Completed

- Product vision and positioning.
- Landing page and web app separation.
- `/app/start` Scelta Guidata UX and decision report prototype.
- Decision Profile, vehicle detail, and Garage Fit contracts.
- Dataset v0.2 with five differentiated mock vehicles.
- Deterministic Advisor v3 scoring, constraints, assessments, confidence, and
  explainability in `apps/api/app/services/advisor/`.
- `POST /advisor/recommendations` and Guided Decision previews using
  `advisor-v3.0`.
- Persistence of the v3 request metadata and item breakdown.
- Historical standalone calibration reports moved to `docs/snapshots/`.
- Standalone `decision_engine/` runtime retired. Advisor v3 is the only ranking
  authority.

## Advisor v3 status

- Complete score: `65% Structural Fit + 35% Preference Fit`.
- Structural pillars: Economics, Practicality, Reliability and Safety,
  Driving, Technology, and Powertrain Fit.
- Preference ranks: `50% / 30% / 20%` for the first three priorities.
- TCO runs now as the versioned `tco-v1` estimate from fixed, documented
  inputs. It can be replaced by a provider without changing the scoring
  contract.
- Reliability, known issues, official recalls, Vehicle DNA, and valuation
  remain explicit specialist prerequisites. Their adapters return
  `insufficient_data` until valid inputs arrive.

See [`docs/advisor-v3.md`](advisor-v3.md) for formulas, status values,
compatibility fields, input contracts, audit data, and benchmark limits.

## Benchmark

The historical calibration covered 12 synthetic scenarios and reported 100%
Top-2 acceptance and MRR 0.958. These are development metrics, not real-world
automotive validation. The source reports are retained under
`docs/snapshots/`.

## Current frontend

The frontend still contains the prototype decision journey and vehicle pages.
It calls the backend for runtime decisions. Mock fallback remains explicit and
is enabled only with `VITE_USE_MOCK_API=true`.

## Current backend

FastAPI owns validation, session orchestration, persistence, and response DTOs.
Advisor v3 owns deterministic eligibility, scoring, module assessments,
confidence, penalties, and ranking. The LLM boundary remains outside ranking.

## Next work

1. Replace synthetic catalog records with reviewed sources.
2. Add the specialist providers documented in `docs/advisor-v3.md`.
3. Run real human calibration and beta telemetry.

The next steps require real data. No future specialist module is claimed to be
live by this document.
