# Task 9 report

## RED/GREEN evidence

- RED: `pytest apps/api/tests/test_advisor_v3_scoring.py -q` — 3 failures; the request rejected v3 priorities and v2 items had no v3 fields.
- GREEN: `pytest apps/api/tests/test_advisor_v3_scoring.py apps/api/tests/test_advisor_scoring.py apps/api/tests/test_advisor_decision_modules.py apps/api/tests/test_advisor_assessments.py -q` — `81 passed`.
- Ruff: `python -m ruff check` on changed scorer, confidence, schema, and scoring tests — `All checks passed`.
- Diff check: `git diff --check` — clean.

## Composition

| Area | Formula |
| --- | --- |
| Structural pillars | Economics .266667; Practicality .177778; Reliability/Safety .222222; Driving .111111; Technology .111111; Powertrain .111111; available weights renormalize |
| Pillars | Economics 45/40/15; Practicality 22/33/25/20; Reliability/Safety 58/42; Driving 48/22/30; Technology 100; Powertrain 100 |
| Preference | First three ordered priorities at 50/30/20; available priorities renormalize |
| Decision | `0.65 * structural_fit + 0.35 * preference_fit`; missing preference is provisional with `decision_score=None` |
| Confidence | `0.45 * profile + 0.35 * evidence + 0.20 * ranking_stability`, clamped and versioned `decision-confidence-v1` |

Missing factors are omitted, never scored as neutral 50. Economics and Practicality remain required for a provisional structural score. Known issues and recalls subtract their module values before composition; module caps remain 8 and 6. Ranking is complete before provisional, then effective score, confidence, price, mileage (missing last), listing ref, and listing ID. Module failures are caught as `insufficient_data`.

## Compatibility and files

`SCORING_VERSION` is `advisor-v3.0`; v2 `score`, component scores, positive/tradeoff factors, evidence, provenance, eligibility, identity, and grouping remain. The item schema now carries v3 decision fields and the expanded priority vocabulary. API/guided tests asserting the pre-v3 version/priority contract were not changed; Task 10 owns that wiring.

Commit: `1a5a008a6c52ca348d827f1c391bfbd5ca89bc45` (`feat(api): unify ranking in Advisor v3`).

Self-review concern: top-level API response and persistence wiring still need Task 10; this task intentionally keeps v3 metadata on each scored item and leaves those integration changes untouched.
