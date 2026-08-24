# Task 1 report: Vehicle Knowledge Profile

## What was integrated

Cherry-picked the nine reviewed functional commits for the Vehicle Knowledge Profile (VPK): migration `0005_vehicle_knowledge_profile.sql`, `VehicleSpecDetail`, curated profile validation and ingestion, source-aware repository reads, listing API exposure, enriched fixtures/schema, focused tests, and contract documentation. The approved Advisor v3 specification and implementation plan were preserved; no cherry-pick conflicts occurred.

## Commits created

- `ac57e29` feat(api): add vehicle knowledge profile schema
- `a91baac` feat(api): define curated vehicle profile input
- `aa84660` fix(api): align vehicle profile validation
- `c908b00` feat(api): persist curated vehicle profiles
- `fde0d5a` fix(api): distinguish profile collection presence
- `cf72ae1` feat(api): expose vehicle knowledge profiles
- `a4afc18` fix(api): keep shared vehicle specs flat
- `03c3c55` docs: describe vehicle knowledge profile contract
- `bf46d9b` fix(api): harden vehicle profile contracts

## Verification

- `/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_catalog_import.py apps/api/tests/test_vehicle_listing_api.py apps/api/tests/test_migrations.py -q`: `24 failed, 43 passed, 5 skipped`; failures are `ModuleNotFoundError: No module named 'jsonschema'` because this absolute path resolves to the main checkout venv, not the isolated worktree.
- `uv run --project apps/api --extra dev python -m pytest apps/api/tests/test_catalog_import.py apps/api/tests/test_vehicle_listing_api.py apps/api/tests/test_migrations.py -q`: `67 passed, 5 skipped`.
- `/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m ruff check apps/api`: `All checks passed!`.
- `git diff --check origin/main...HEAD`: clean. Worktree is clean after committing this report.

## Files and conflicts

The integration touched the intended API, migration, fixture, documentation, and test files from the reviewed sequence. No conflicts were encountered. The worktree-local `.venv` created by `uv run` is ignored and not committed.

## Self-review and concerns

The payload matches the requested dependency boundary: it consumes schema through `0004_curated_catalog.sql` and produces migration `0005`, `VehicleSpecDetail`, curated ingestion, and source-aware reads. The only concern is the brief's absolute test interpreter path targets the main checkout; use the worktree interpreter or `uv run --project apps/api --extra dev` for reproducible green tests.
