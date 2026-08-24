# Task 8 report

## Evidence

- `apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_assessments.py apps/api/tests/test_advisor_decision_modules.py apps/api/tests/test_advisor_scoring.py -q` -> `69 passed`.
- `apps/api/.venv/bin/ruff check ...` -> `All checks passed!`.
- `git diff --check` -> clean.

## Contracts

- `safety-v1`: available from curated rating percentages, or stars when percentages are absent; otherwise `insufficient_data`.
- `reliability-v1`: only explicit specialist assessment input; absent input is `insufficient_data`.
- `vehicle-dna-v1`: explicit calibrated factor assessments only; optional feature evidence is exposed without deriving a universal score.
- `known-issues-v1`: generation/spec/engine/transmission/year applicability is checked before severity; conflicts do not apply; unknown applicability warns; penalty cap 8.
- `recalls-v1`: open applicable recalls penalize, resolved recalls do not, unknown applicability warns; penalty cap 6.

## Files and review

Changed five specialist modules and `test_advisor_assessments.py`; commit `5df6dcde6a975fecf250d16c8451a842a2fa4a4`.

Self-review: no providers, database writes, dependencies, ranking, neutral fallback, or mocked specialist data. Known ceiling: explicit specialist input adapters intentionally defer calibration and official resolution to later tasks.
