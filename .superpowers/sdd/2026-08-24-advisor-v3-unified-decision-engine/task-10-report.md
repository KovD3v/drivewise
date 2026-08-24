# Task 10 report

## Evidence

- RED: the new API test lacked `request_payload.active_versions`; the Guided sample lacked `children_count` (`2 failed`).
- GREEN/focused: `/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_api.py apps/api/tests/test_guided_decisions.py apps/api/tests/test_migrations.py apps/api/tests/test_advisor_v3_scoring.py apps/api/tests/test_advisor_scoring.py apps/api/tests/test_advisor_decision_modules.py apps/api/tests/test_advisor_assessments.py -q` -> `110 passed, 5 skipped`.
- Ruff: `All checks passed!`; `git diff --check` clean. The five skips are database/environment-gated tests; `TEST_DATABASE_URL` was unset.

## Contract and persistence

- POST `/advisor/recommendations` now returns `advisor-v3.0` and preserves additive item fields: structural/preference fit, decision score/confidence, pillars, penalties, strengths, missing factors, module versions, assumptions, score composition, evidence, and provenance.
- `request_payload` keeps the normalized flat request and adds `normalized_profile` plus `active_versions` (`scoring`, `confidence`, and sorted module versions).
- `score_breakdown` JSONB keys include `decision_status`, `decision_score`, `decision_confidence`, `confidence_components`, `structural_fit`, `preference_fit`, `pillar_scores`, `penalties`, `missing_factors`, `module_versions`, `assumptions`, `component_scores`, `positive_factors`, `tradeoffs`, `evidence`, and `provenance`, plus `legacy_compatibility.label` for retained `normalized_weights`.
- Run/item writes remain one connection transaction; an item-write exception is covered and cannot call `mark_run_completed`.

## Guided Decision

- Explicit Italian extraction maps `usage`, `children_count`, `passengers_usual`, `automatic_required`, and `constraint_modes` into the typed `DecisionProfile`; deterministic questions are additive and preserve reopen/version conflict behavior.
- Guided builds one `AdvisorRecommendationRequest` and calls `score_recommendations`; preview status is `blocked`, `insufficient_inventory`, `provisional`, or `ready` according to the scored items.

## Files, commit, self-review

- Files: advisor router/repository/scoring compatibility label; Guided schema, engine, interpreter, questions; API and Guided tests; this report.
- Implementation commit before report refresh: `00ee25c` (`feat(api): expose and persist Advisor v3`).
- Self-review: no migration, ranking path, provider, dependency, or frontend change. DB round-trip remains unverified until `TEST_DATABASE_URL` is configured.
