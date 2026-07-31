# Plan 003: Make rankable inventory measurable and give the advisor a real corpus

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat 70bfe86..HEAD -- apps/api/app/repositories/advisor.py apps/api/app/ingestion/catalog.py data/fixtures/catalog/ docs/catalog-v1.schema.json`
>
> **IMPORTANT — this repo has a dirty working tree.** This plan was written
> against the *working tree* at commit `70bfe86`, which has extensive
> uncommitted changes. A clean `git diff` against `70bfe86` will be misleading.
> Trust the "Current state" excerpts: read each cited file and confirm the
> excerpt matches disk. Treat a mismatch as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: LOW (adds tooling and fixture data; changes no runtime logic)
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `70bfe86`, 2026-07-26

## Why this matters

The advisor's scoring engine is substantial — 27 exclusion reasons, per-metric
provenance, normalized priority weights, stable tie-breaking. The inventory it
runs on is **two offers for one fictional car.**

Verified: `AdvisorRepository.list_candidates` inner-joins `import_runs` on
`status = 'completed'`
(`apps/api/app/repositories/advisor.py:101-103`), so the five seed vehicles from
`0003_seed_initial_vehicles.sql` — which have no `import_run_id` — are dropped
structurally. Their source row is inserted without a `ranking_permission`
(`0003_seed_initial_vehicles.sql:1`) and `0004_curated_catalog.sql` adds that
column as `NOT NULL DEFAULT 'not_permitted'`, so they are doubly unrankable. The
only `permitted` source in the repository is
`data/fixtures/catalog/catalog-v1.synthetic.json`, which contains **1 vehicle,
2 variants, 2 listings**.

Two consequences: (1) nobody can tell how close the pipeline is to producing
usable rankings, because there is no measurement; (2) every downstream feature —
comparison views, price history, UI work on ranked results — is built and
demoed against a single fictional car, so real ranking behavior is untested and
unseen.

This plan fixes both without waiting on any licensing decision: it adds a
readiness measurement, and it grows the synthetic corpus to the point where the
advisor exercises every code path it has. Acquiring **real** licensed inventory
is a separate, decision-gated step, scoped out below.

### What this plan deliberately does NOT do

It does not onboard a real data source. Which Italian sources may legally be
ranked is a licensing decision only the maintainer can make — `docs/catalog-import.md`
already encodes the rule that only `ranking_permission: 'permitted'` sources may
contribute, and `.gitignore` already excludes `data/private/catalog/`. Step 4
writes the checklist that decision needs; it does not pre-empt it.

## Current state

### Files in play

- `apps/api/app/repositories/advisor.py` — `list_candidates` (the eligibility
  join) and `count_excluded_candidates` (the exclusion classifier). **Read-only
  for this plan.**
- `apps/api/app/ingestion/catalog.py` (1133 lines) — the importer.
- `apps/api/scripts/import_catalog.py` (117 lines) — CLI with `--check` /
  `--write`. Use it as the structural exemplar for the new script.
- `docs/catalog-v1.schema.json` — the snapshot schema.
- `data/fixtures/catalog/catalog-v1.synthetic.json` — the corpus to grow.
- `docs/catalog-import.md` — the import contract.

### The catalog v1 snapshot shape (authoritative — from the schema)

Top level requires `schema_version`, `sources`, `vehicles`, `variants`,
`listings`.

| Object | Required fields |
|---|---|
| `source` | `source_key`, `name`, `source_type`, `market`, `ranking_permission`, `url`, `license` |
| `vehicle` | `canonical_key`, `model_family_key`, `make`, `model`, `model_year`, `market`, `source_key`, `source_url`, `observed_at` |
| `variant` | `variant_key`, `vehicle_key`, `trim`, `is_default`, `body_style`, `fuel_type`, `seats`, `cargo_volume_liters`, `source_key`, `source_url`, `observed_at` |
| `listing` | `listing_ref`, `variant_key`, `title`, `price_eur`, `condition`, `is_active`, `source_key`, `source_url`, `observed_at` |
| `provenanceClaim` | `source_key`, `source_url`, `observed_at`, `supported_metrics` |

`source_type` must be one of `manual_seed`, `public_dataset`,
`curated_internal`. `ranking_permission` must be one of `permitted`,
`not_permitted`, `manual_validation_only`.

### What makes an offer rankable (from `list_candidates`)

An offer/variant pair reaches the scorer only if **all** hold. This is the
checklist your fixture must satisfy:

- `upper(vehicles.market) = 'IT'` and `upper(sources.market) = 'IT'`
- `sources.ranking_permission = 'permitted'`
- `listings.is_active IS TRUE`
- `listings.last_seen_at >= now() - 30 days` (`FRESHNESS_DAYS = 30`)
- `listings.valid_until IS NULL OR >= now()`
- non-blank `listings.source_url`, `sources.name`, `sources.license`
- non-blank `vehicles.model_family_key`, `vehicle_specs.variant_key`
- joined `import_runs.status = 'completed'`
- `price_eur IS NOT NULL`; `condition IN ('new','used','certified')`;
  `mileage IS NOT NULL` unless `condition = 'new'`
- `fuel_type` in the 7-value enum, not PHEV; `body_style` in the 9-value enum
- `seats` and `cargo_volume_liters` not null
- electric ⇒ `energy_consumption_kwh_100km` and `wltp_range_km` not null;
  non-electric ⇒ `consumption_l_100km` not null
- **per-metric provenance** from a permitted source for `body_style`,
  `fuel_type`, `seats`, `cargo_volume_liters`, plus `consumption_l_100km`
  (non-electric) or `energy_consumption_kwh_100km` + `wltp_range_km` (electric).
  Provenance metadata must list these names under `supported_metrics`.

The two enums, verbatim from `apps/api/app/services/advisor/scoring.py`:

```
fuel_type:  diesel, electric, full_hybrid_petrol, hybrid_petrol,
            mild_hybrid_petrol, petrol, petrol_lpg
body_style: city_car, crossover, hatchback, mpv, sedan, small_hatchback,
            suv, van, wagon
```

### The freshness trap — read this before writing fixture data

`last_seen_at` must be within 30 days of *now*, so a committed fixture with
fixed dates stops being rankable 30 days after you write it. A naive coverage
test would pass today and silently fail next month.

**Resolution, mandatory:** the coverage test in Step 3 must pin evaluation time
rather than use the wall clock. `score_recommendations` already accepts
`as_of: datetime | None` (`apps/api/app/services/advisor/scoring.py:179-185`),
and `AdvisorRepository.list_candidates` / `count_excluded_candidates` both accept
`as_of` too. Pass a fixed `as_of` derived from the fixture's own `observed_at`
values. Never call `datetime.now()` in the test.

### Repo conventions to match

- **Scripts** live in `apps/api/scripts/`, are argparse-based, load `.env`, and
  are explicit about read vs. write. `import_catalog.py` refuses to write unless
  `--write` is passed and `migrate.py` refuses placeholder database URLs. New
  scripts must be **read-only by default**. Read `apps/api/scripts/import_catalog.py`
  end to end before writing Step 1.
- **Fixtures are synthetic and labelled.** The existing fixture uses the
  fictional make `ACME` with `model: Metro`. Keep inventing fictional
  manufacturers. **Do not use real makes or models** — attaching invented specs
  and prices to a real vehicle would misrepresent data the project has not
  sourced, which is exactly what this codebase's provenance design exists to
  prevent.
- **Tests** are plain pytest in `apps/api/tests/`, named `test_*.py`. See
  `apps/api/tests/test_catalog_import.py` for fixture-driven importer tests.
- `AGENTS.md` is binding — read it first.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Backend tests | `uv run --frozen --project apps/api --extra dev pytest apps/api -q` | `143 passed, 4 skipped` baseline |
| Backend lint | `uv run --frozen --project apps/api --extra dev ruff check apps/api` | `All checks passed!` |
| Validate fixture | `uv run --project apps/api python apps/api/scripts/import_catalog.py --path data/fixtures/catalog/catalog-v1.synthetic.json --check` | validation passes, no DB writes |

**Do not run any command with `--write`, and do not run `migrate.py`.** Both
write to a real database. Everything in this plan is verifiable without one.

## Scope

**In scope**:

- `apps/api/scripts/catalog_status.py` (create)
- `apps/api/app/repositories/advisor.py` — **only** if a read-only aggregate
  query is needed for Step 1. Adding a new read method is allowed; changing
  `list_candidates` or `count_excluded_candidates` is not.
- `data/fixtures/catalog/catalog-v1.synthetic.json` (grow)
- `apps/api/tests/test_catalog_coverage.py` (create)
- `apps/api/tests/test_catalog_status_script.py` (create)
- `docs/source-review.md` (create)
- `docs/catalog-import.md`, `README.md` (document the new script)
- `plans/README.md` (status row only)

**Out of scope** (do NOT touch):

- `apps/api/app/services/advisor/scoring.py` — no scoring change of any kind.
- The `WHERE` clause of `list_candidates` and the `CASE` ladder in
  `count_excluded_candidates`. If the fixture fails to rank, **fix the fixture,
  never the eligibility rules.** Loosening a rule to make data pass would
  destroy the provenance guarantee that is this project's core value.
- `apps/api/migrations/` — no migration. If you think you need one, STOP.
- Real source onboarding, crawling, Firecrawl, embeddings.
- `data/private/catalog/` — gitignored, and not yours to create.
- `apps/web/` — no frontend change in this plan.

## Git workflow

- Branch: `advisor/003-rankable-inventory-pipeline`
- Conventional Commits, e.g. `feat(api): report rankable catalog inventory`.
- Commit the fixture growth separately from the tooling — the fixture diff is
  large and mechanical, and mixing them makes review harder.
- Do NOT push, open a PR, or merge.

## Steps

### Step 1: Add a read-only inventory readiness report

Create `apps/api/scripts/catalog_status.py`, modelled structurally on
`apps/api/scripts/import_catalog.py` (argparse, `.env` loading, explicit exit
codes). It connects to the database configured by `DATABASE_URL`, **reads only**,
and prints:

1. Total listings, and how many are rankable — reuse
   `AdvisorRepository.list_candidates(as_of=...)` and report `len()`.
2. Exclusion counts by reason — reuse
   `AdvisorRepository.count_excluded_candidates(as_of=...)`, printed in
   descending count order.
3. Rankable coverage: counts grouped by `body_style`, by `fuel_type`, and by
   `condition` group (`new` vs `used`), plus min/max rankable `price_eur`.
4. A line naming any `body_style` or `fuel_type` enum value with **zero**
   rankable offers — these are the blind spots a maintainer needs to see.

Add `--as-of <ISO8601>` so the report can be run at a pinned time, defaulting to
now. The script must have no `--write` flag and must never execute
`INSERT`/`UPDATE`/`DELETE`.

Document it in `README.md` under "Checks" and in `docs/catalog-import.md`.

**Verify**:
- `uv run --frozen --project apps/api --extra dev ruff check apps/api` → `All checks passed!`
- `uv run --project apps/api python apps/api/scripts/catalog_status.py --help` → prints usage, exit 0
- `grep -nE "INSERT|UPDATE|DELETE" apps/api/scripts/catalog_status.py` → no matches

### Step 2: Grow the synthetic catalog to a real corpus

Expand `data/fixtures/catalog/catalog-v1.synthetic.json` so it satisfies this
coverage matrix. Every offer must pass the full rankability checklist quoted in
"Current state" — including per-metric provenance claims.

**Required coverage:**

- **≥ 24 vehicles** across **≥ 6 fictional makes**, `market: "IT"`.
- **All 9 `body_style` values** appear on at least two rankable offers each.
- **All 7 `fuel_type` values** appear on at least two rankable offers each.
- **Both condition groups**: ≥ 8 offers with `condition: "new"` (no `mileage`
  needed) and ≥ 16 with `"used"` or `"certified"` (each with `mileage`).
- **Price spread** €6,000–€60,000, with ≥ 4 offers under €12,000 and ≥ 4 above
  €35,000, so budget filtering and the `above_budget_tolerance` path are both
  exercised.
- **Every `primary_use` gets plausible winners**: at least two offers that score
  well for each of `city`, `highway`, `family`, `work`, `new_driver` — i.e.
  small cheap city cars *and* large high-cargo vehicles must both exist.
- **≥ 3 model families with multiple variants** (same `model_family_key`,
  different `variant_key`) so the one-per-family dedupe in
  `score_recommendations` is exercised.
- **≥ 2 deliberately non-rankable offers** to prove the exclusion path works and
  keep `count_excluded_candidates` meaningful: e.g. one from a second source with
  `ranking_permission: "not_permitted"`, and one with `is_active: false`.
  Do **not** create a PHEV — `unsupported_phev` is checked before the enum, and
  the catalog importer restricts `fuel_type` to the checked-in enum anyway.

**Data realism rules:**

- EV variants need `energy_consumption_kwh_100km` **and** `wltp_range_km`; give
  at least one EV `wltp_range_km >= 250` and one `< 250` so the
  `insufficient_highway_ev_range` rule is covered.
- Non-EV variants need `consumption_l_100km`.
- Values must be internally plausible: a `city_car` with 700 L of cargo or a
  `van` with 2 seats and 3.0 L/100 km will make the corpus useless for judging
  ranking output. Keep consumption, cargo, seats, and price coherent with the
  body style.
- Set every listing's `observed_at` to **one single shared date** and record that
  date in the fixture. Step 3's test pins `as_of` to it. Using many scattered
  dates makes the test's `as_of` choice arbitrary.
- Give each variant `provenance_claims` whose `supported_metrics` cover exactly
  the metrics that variant actually populates. A claim for a null field is
  rejected by the importer (`docs/catalog-import.md`).

Here is the existing single vehicle's shape to extend — keep this style:

```
sources:  [{source_key: "drivewise-synthetic-catalog", ranking_permission: "permitted", ...}]
vehicles: [{canonical_key: "it-acme-metro-2026", model_family_key: ..., make: "ACME", ...}]
variants: ["it-acme-metro-2026-city-petrol", "it-acme-metro-2026-city-electric"]
listings: [{listing_ref: "synthetic-metro-petrol-new", condition: "new", price_eur: 17500},
           {listing_ref: "synthetic-metro-electric-used", condition: "used", price_eur: 22000}]
```

**Verify**:
- `uv run --project apps/api python apps/api/scripts/import_catalog.py --path data/fixtures/catalog/catalog-v1.synthetic.json --check` → validation passes
- `python3 -c "import json;d=json.load(open('data/fixtures/catalog/catalog-v1.synthetic.json'));print({k:len(v) for k,v in d.items() if isinstance(v,list)})"`
  → `vehicles` ≥ 24, `listings` ≥ 26
- `uv run --frozen --project apps/api --extra dev pytest apps/api -q` → `143 passed, 4 skipped`

### Step 3: Lock the coverage in with a test

Create `apps/api/tests/test_catalog_coverage.py`. It must **not** need a
database: load the fixture JSON, transform it into the candidate-dict shape that
`score_recommendations` consumes, and assert on the scored result. Read
`apps/api/tests/test_advisor_scoring.py` first — it already builds candidate
dicts by hand, and its helpers show the exact expected shape.

Assertions:

1. Every `body_style` enum value appears on ≥ 2 rankable candidates.
2. Every `fuel_type` enum value appears on ≥ 2 rankable candidates.
3. For each of the five `primary_use` values, `score_recommendations` with a
   €60,000 budget returns a non-empty `new` group and a non-empty `used` group.
4. The deliberately non-rankable offers from Step 2 are excluded, with the
   expected reason keys present in `excluded_counts_by_reason`.
5. Multi-variant families yield at most one item per `model_family_key` per
   group.

Pass a **fixed** `as_of` built from the fixture's shared `observed_at` date.
Add a comment explaining why: a wall-clock `as_of` would make this test start
failing 30 days after the fixture was written.

**Verify**: `uv run --frozen --project apps/api --extra dev pytest apps/api/tests/test_catalog_coverage.py -q`
→ all pass. Then full suite → `143 + N passed, 4 skipped`.

### Step 4: Add a `catalog_status.py` smoke test

Create `apps/api/tests/test_catalog_status_script.py`, modelled on the existing
`apps/api/tests/test_plan_embeddings_script.py` and
`test_migrate_script.py` (which test script behavior without a live database —
read them for the mocking approach).

Cover: `--help` exits 0; a missing/placeholder `DATABASE_URL` exits non-zero with
a clear message rather than a traceback; the report formats a stubbed repository
result correctly, including the zero-coverage blind-spot line.

**Verify**: `uv run --frozen --project apps/api --extra dev pytest apps/api -q`
→ all pass.

### Step 5: Write the source-review checklist

Create `docs/source-review.md` — the procedure for taking a candidate data source
from discovery to `ranking_permission: 'permitted'`. This is documentation only;
it onboards no source.

It must capture, as a checklist a human fills in per source:

- Source identity: `source_key`, name, URL, `source_type`.
- **Licence review**: what the terms permit, specifically whether derived
  rankings and stored snapshots are allowed, and the URL of the terms reviewed.
- Whether attribution is required, and where it would surface in the UI.
- Robots/ToS position on automated access, if access would be automated.
- Which metrics the source is trusted to support (the `supported_metrics` it may
  claim) and which it may not.
- Freshness: how often it is re-observed, versus the 30-day `FRESHNESS_DAYS`
  window.
- The reviewer's name and date, and the resulting `ranking_permission` value with
  a one-line rationale.
- An explicit note that `not_permitted` and `manual_validation_only` sources may
  still be imported for review — they simply never reach rankings.

Cross-link it from `docs/catalog-import.md`.

**Verify**: `grep -c "" docs/source-review.md` → non-zero; the file contains no
credentials, tokens, or private URLs.

## Test plan

| Test | File | Case |
|---|---|---|
| Body-style coverage | `test_catalog_coverage.py` (new) | all 9 values, ≥2 rankable each |
| Fuel-type coverage | `test_catalog_coverage.py` | all 7 values, ≥2 rankable each |
| Every use case ranks | `test_catalog_coverage.py` | 5 `primary_use` values, both groups non-empty |
| Exclusions still fire | `test_catalog_coverage.py` | non-permitted + inactive offers excluded with expected reasons |
| Family dedupe | `test_catalog_coverage.py` | ≤1 item per `model_family_key` per group |
| Script help / bad DB URL | `test_catalog_status_script.py` (new) | exit codes and messages |
| Report formatting | `test_catalog_status_script.py` | stubbed repo → expected lines |
| Fixture still imports | `test_catalog_import.py` (existing) | passes unchanged |

Structural patterns: `test_advisor_scoring.py` for candidate dicts,
`test_plan_embeddings_script.py` for script tests, `test_catalog_import.py` for
fixture handling.

## Done criteria

ALL must hold:

- [ ] `uv run --frozen --project apps/api --extra dev pytest apps/api -q` → all pass, ≥8 new tests
- [ ] `uv run --frozen --project apps/api --extra dev ruff check apps/api` → `All checks passed!`
- [ ] `import_catalog.py --check` passes on the grown fixture
- [ ] `catalog_status.py --help` exits 0
- [ ] `grep -nE "INSERT|UPDATE|DELETE" apps/api/scripts/catalog_status.py` → no matches
- [ ] `git diff apps/api/app/services/advisor/scoring.py` → **empty**
- [ ] `git diff apps/api/app/repositories/advisor.py` → contains no change to any
      `WHERE`, `CASE`, or `JOIN` clause (new read-only method only)
- [ ] `ls apps/api/migrations/` → no new file
- [ ] `grep -rniE "\b(fiat|toyota|volkswagen|dacia|tesla|renault|peugeot|ford)\b" data/fixtures/catalog/` → no matches (fictional makes only)
- [ ] `grep -rn "datetime.now\|date.today" apps/api/tests/test_catalog_coverage.py` → no matches (pinned `as_of`)
- [ ] `docs/source-review.md` exists
- [ ] `plans/README.md` status row for 003 updated

## STOP conditions

Stop and report back — do not improvise — if:

- The code at any location in "Current state" does not match the excerpt.
- **A fixture offer will not become rankable and the only way you can see to fix
  it is editing `list_candidates`, `count_excluded_candidates`, or
  `scoring.py`.** The eligibility rules are the product; the fixture is the
  variable. Report which rule blocks you and why.
- You conclude a migration is needed.
- The importer rejects a `provenance_claims` array and you cannot satisfy it from
  `docs/catalog-import.md` alone.
- Any verification fails twice after a reasonable fix attempt.
- The coverage matrix in Step 2 proves impossible to satisfy within the existing
  enums — report the specific gap rather than widening an enum.

## Maintenance notes

- **The fixture's shared `observed_at` date is load-bearing.** It is what
  Step 3's pinned `as_of` derives from. If someone edits fixture dates, the
  coverage test's `as_of` must move with them.
- Local demos still hit the freshness window: a fixture imported months later has
  stale `last_seen_at` and will rank nothing at wall-clock time. A follow-up
  worth considering is an `import_catalog.py --restamp-observed-now` flag for
  local development only. Deliberately out of scope here.
- `catalog_status.py` is the readiness gauge for real onboarding. When the first
  real source lands, its exclusion histogram is the fastest way to see which
  metrics that source fails to provide.
- A reviewer should scrutinize: that no eligibility rule moved, that the fixture
  uses fictional makes only, that provenance claims match populated fields, and
  that the coverage test does not read the wall clock.
- Deliberately deferred: real source onboarding (needs the Step 5 checklist
  filled in by a human), and PHEV support (currently excluded by design —
  a product decision, not a data gap).
