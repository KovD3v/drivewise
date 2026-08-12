# DriveWise — Current Status

_Last updated: 2026-08-12_

## Overall phase
**MVP implementation — transition from prototype to integrated product**

## Completed
- Product vision and positioning.
- Landing Page concept and implementation in Lovable.
- Separation Landing / Web App.
- `/app/start` Scelta Guidata UX and mock journey.
- Decision Profile specification.
- Decision Report mock.
- Decision Vehicle Page with decision-oriented content.
- Garage Fit UX concept.
- Dataset v0.2 with five differentiated sample vehicles.
- Decision Engine Python iterations v0.1 → v1.0.
- Data confidence / freshness model.
- Explainability payload.
- Synthetic calibration benchmark.
- Decision Engine v1.0 frozen for MVP contract.

## Decision Engine v1.0 benchmark
- Decision Score = 65% Structural Fit + 35% Preference Fit.
- Preference ranks = 50% / 30% / 20%.
- 12 synthetic calibration scenarios.
- Top-2 acceptance on synthetic calibration: 100%.
- MRR: 0.958.
- 11 automated tests passing at freeze time.

These are development/calibration metrics, not real-world automotive validation.

## Current frontend
Lovable URL used during prototyping:
`https://drivewise-decision-hub.lovable.app/`

The frontend currently relies primarily on local/mock data. The next technical objective is to replace mock decision execution with backend REST calls while preserving the current UX.

## Current backend
Repository already contains backend/data work and documentation. The new assignment is to expose and integrate the frozen Python Decision Engine v1.0 cleanly rather than re-implement scoring independently.

## NEXT — highest priority
**Tommaso: Backend API Foundation + Decision Engine integration.**

See `docs/TOMMASO_BACKLOG.md`.

Expected first vertical slice:
`Lovable /app/start → POST decision API → Python Decision Engine v1.0 → ranked response → Decision Report UI`

## After first vertical slice
1. Vehicle detail APIs.
2. Session persistence.
3. Dataset ingestion/validation.
4. Replace all hardcoded Vehicle Page data.
5. Grow from 5 sample vehicles to an MVP catalog of 30–50 validated vehicles.
6. Real human calibration exercise.
7. Beta telemetry and feedback.

## Important constraint
Do not redesign the frontend unless a backend integration need makes a change unavoidable. The near-term work is functional integration and data quality, not another UI redesign cycle.
