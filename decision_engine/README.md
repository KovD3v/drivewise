# DriveWise Decision Engine v1.0

Deterministic, API-ready Decision Intelligence engine for the DriveWise MVP.

## Frozen MVP rule

`Decision Score = 65% Structural Fit + 35% Preference Fit`

Preference Fit uses the user's ranked top-three priorities weighted 50% / 30% / 20%.

## Structural pillars
- Economics
- Practicality
- Reliability & Safety
- Driving
- Technology
- Powertrain Fit

## Pipeline
`Decision Profile → Hard Filters → TCO → Garage Fit → Powertrain Fit → Pillars → Weight Engine → Penalties → Preference Alignment → Decision Score → Confidence → Explainability → Ranking`

## Confidence
Decision Confidence is separate from Decision Score. It combines profile completeness, vehicle data quality and ranking stability. Data quality considers source reliability, freshness, verification and domain confidence.

## API-ready output
Use `engine.api_payload(profile, limit=5)`.

Each ranking item includes Decision Score, Decision Confidence, Data Quality, Pillar scores, strengths, trade-offs, penalties and structured explainability.

## LLM boundary
The LLM must not calculate or override ranking. It may interpret user free text and turn structured explainability into natural-language output.

## Validation status
At the v1.0 freeze the engine passed 11 automated tests and the synthetic 12-profile calibration benchmark reached 100% Top-2 acceptance and MRR 0.958. These are development metrics, not real-world automotive validation.

See `FINAL_CALIBRATION_REPORT.md` for details.
