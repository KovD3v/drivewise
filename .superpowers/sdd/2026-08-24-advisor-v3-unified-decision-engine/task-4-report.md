# Task 4 report: source-aware decision inputs

## RED

Command:

```text
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_api.py -q
```

Result: `1 failed, 4 passed, 1 skipped`; the new candidate test failed with `KeyError: 'decision_context'`.

## GREEN

Command:

```text
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_api.py -q
```

Result: `5 passed, 1 skipped`.

Command:

```text
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/ruff check apps/api/app/repositories/advisor.py apps/api/tests/test_advisor_api.py
```

Result: `All checks passed!`.

The combined requested command also ran `apps/api/tests/test_catalog_import.py`; 24 tests failed before execution because the environment lacks the pre-existing `jsonschema` dependency (`ModuleNotFoundError: No module named 'jsonschema'`). The focused advisor tests and Ruff pass. The database-backed advisor persistence test was skipped because `TEST_DATABASE_URL` is unavailable.

## Mapping and trust gates

The existing listing/spec/import/freshness/market/permission/provenance eligibility SQL remains unchanged. The candidate SELECT now reads the Task 1 scalar profile fields and aggregates maintenance, safety ratings, safety features, and technology/comfort features. Child aggregates include source ID, source name, source URL, and observed timestamp, and only include children whose source has `ranking_permission = 'permitted'`. Existing v2 `vehicle`, `spec`, `offer`, `source`, and `provenance` keys are preserved. `decision_context` uses null-safe scalar mapping and returns empty child arrays when no permitted children exist. No reliability, issues, recalls, or DNA data was added.

## Files and self-review

- `apps/api/app/repositories/advisor.py`: query and candidate mapper.
- `apps/api/tests/test_advisor_api.py`: source-aware candidate repository test.

Reviewed SQL aliases against migration `0005_vehicle_knowledge_profile.sql`, checked null behavior, preserved exact listing/spec/offer identity, and ran `git diff --check` successfully.

## Commit

SHA: `6bd8ab1a45e39f24bf067373ee07fae2ac26f51a` (implementation commit).

## Concerns

Live PostgreSQL syntax and catalog tests could not be fully verified without `TEST_DATABASE_URL` and the missing `jsonschema` package.
