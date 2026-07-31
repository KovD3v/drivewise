# Plan 002: Add Italian ownership taxes (bollo, IPT) to cost estimates

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat 70bfe86..HEAD -- apps/api/app/services/advisor/ apps/api/app/schemas/advisor.py apps/api/migrations/ apps/api/app/ingestion/catalog.py`
>
> **IMPORTANT — this repo has a dirty working tree.** This plan was written
> against the *working tree* at commit `70bfe86`, which has extensive
> uncommitted changes. A clean `git diff` against `70bfe86` will be misleading.
> Trust the "Current state" excerpts below: read each cited file and confirm the
> excerpt matches disk. Treat a mismatch as a STOP condition.
>
> **THIS PLAN HAS A BLOCKING INPUT.** Step 0 requires a reviewed tax-rate table
> that only the maintainer can supply. Do not invent rates. See Step 0.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (adds a migration; introduces figures that must be sourced)
- **Depends on**: none (but see Step 0 blocking input)
- **Category**: direction
- **Planned at**: commit `70bfe86`, 2026-07-26

## Why this matters

Drivewise estimates what a car costs to run, but only counts energy. The code is
explicit about it — `apps/api/app/services/advisor/scoring.py:152-154` states:

```python
(
    "The running_cost component covers energy only; maintenance, tax, "
    "insurance, depreciation, and financing are excluded."
),
```

For an Italian buyer, **bollo auto** (the annual regional vehicle tax) is a
first-order cost of ownership, and **IPT** (Imposta Provinciale di Trascrizione)
is a real, non-trivial cost on any used purchase. Both are *deterministic
functions of data the schema is already designed to hold*: engine power and euro
emission class. That makes them an unusually good fit for this codebase, which
prizes deterministic, provenance-carrying numbers over estimates.

After this plan, `/advisor/model-analysis` reports annual road tax and (for used
offers) transfer tax, and the advisor's per-item `evidence` carries the annual
bollo figure. Ranking behavior does not change — see "Deliberate scope limit".

### Deliberate scope limit — read before starting

This plan **surfaces** the taxes; it does **not** fold them into the
`running_cost` score component or change any ranking.

Reasons: (1) changing a score component requires bumping `SCORING_VERSION` and
rewriting a large body of test expectations in
`apps/api/tests/test_advisor_scoring.py`, which is a separate, larger change;
(2) the UI already labels that component honestly — `componentLabels.running_cost`
in `apps/web/src/views/Advisor.tsx` reads `'Costo energia'` ("energy cost"), not
"running cost" — so there is no active mislabeling to fix; (3) whether tax
belongs in the weighted score at all is a product decision, not an
implementation detail.

If you find yourself editing `_score_candidate`'s `raw_scores` dict or
`BASE_WEIGHTS`, you have left this plan's scope. That is a STOP condition.

## Step 0 — BLOCKING INPUT: the rate table

Bollo and IPT rates are set by law, vary by region/province, and change. This
plan will not have you guess them.

**Before writing any calculation code, confirm you have been given a reviewed
rate table** containing, at minimum:

- The €/kW rate bands for bollo (the rate below and above the 100 kW threshold),
  per euro emission class.
- The treatment of battery-electric vehicles (national exemption period and what
  applies afterwards).
- Whether the `superbollo` surcharge on high-power vehicles is in scope.
- The IPT basis for used transfers.
- For each: the **source name, source URL, and observation date**.

**If you have not been given this table, STOP and report that Step 0 is
unsatisfied.** Do not substitute values from your own knowledge, do not copy
rates from a web search, and do not leave `TODO` placeholders in shipped code.
Wrong tax figures shown to a buyer are worse than no figures, and this
repository's entire design premise is that user-facing numbers are sourced.

The rate table is data for Step 2. Everything in Step 1 can proceed without it.

## Current state

### Files in play

- `apps/api/migrations/` — numbered, idempotent SQL. Latest is
  `0004_curated_catalog.sql`. Your new file will be `0005_*.sql`.
- `apps/api/app/services/advisor/energy_prices.py` — **the exemplar to copy.**
  It is the repo's established pattern for a sourced, dated, versioned
  assumption table shared between services.
- `apps/api/app/services/advisor/model_analysis.py` — builds
  `ModelAnalysisCostSummary`. Contains `_estimate_costs`, `_annual_maintenance`,
  `_monthly_energy_cost`, `_depreciation_3y`.
- `apps/api/app/services/advisor/scoring.py` — builds the per-item `evidence`
  dict in `_score_candidate`.
- `apps/api/app/schemas/advisor.py` — `ModelAnalysisCostSummary` at line 147.
- `apps/api/app/ingestion/catalog.py` (1133 lines) — the catalog importer.
- `docs/catalog-v1.schema.json` — the JSON Schema for catalog snapshots.
- `apps/web/src/views/ModelAnalysis.tsx` — renders the cost summary.

### The cost summary you will extend

`apps/api/app/schemas/advisor.py:147-152`:

```python
class ModelAnalysisCostSummary(BaseModel):
    market_reference_price_eur: float | None = None
    estimated_annual_maintenance_eur: float | None = None
    estimated_monthly_energy_eur: float | None = None
    estimated_depreciation_3y_eur: float | None = None
    notes: list[str] = Field(default_factory=list)
```

### The sourced-assumption pattern to follow

`apps/api/app/services/advisor/energy_prices.py` (excerpt) — match this shape,
including the module docstring warning and the version constant:

```python
ENERGY_ASSUMPTION_VERSION = "it-energy-2026-07-16-v1"

MIMIT_SOURCE_NAME = "MIMIT regional fuel-price averages"
MIMIT_SOURCE_URL = "https://www.mimit.gov.it/it/prezzo-medio-carburanti/regioni"

# Date the figures below were actually observed/published. This is
# intentionally a fixed historical date rather than something derived from
# "now": it records when the underlying MIMIT/ARERA data was captured, not
# when the code happens to run.
ENERGY_PRICES_OBSERVED_AT = date(2026, 7, 16)

LIQUID_ENERGY_PRICES_EUR_PER_LITER: dict[str, float] = {
    "petrol": 1.91662,
    ...
}
```

Provenance entries are emitted as `AdvisorMetricProvenance`
(`apps/api/app/schemas/advisor.py:209-214`):

```python
class AdvisorMetricProvenance(BaseModel):
    metric: str
    source_name: str
    source_url: str
    observed_at: date | datetime
```

`_build_provenance` in `scoring.py` appends the energy-rate entry to every
item's provenance list. Your bollo rate must get the same treatment.

### The data problem you must fix first

Bollo is assessed on **kilowatts**. The schema stores `horsepower` and **never
declares its unit**:

- `apps/api/migrations/0002_create_mvp_schema.sql:22` —
  `horsepower integer CHECK (horsepower IS NULL OR horsepower > 0)`
- `docs/catalog-v1.schema.json:134` —
  `"horsepower": { "type": ["integer", "null"], "exclusiveMinimum": 0 }`
- `docs/data-model.md:78` — lists `horsepower` with no unit

The seed data implies Italian metric horsepower (CV): the 2024 Fiat Panda is
seeded with `horsepower = 70`, which matches its 70 CV / 51 kW rating. But
"implies" is not "declares", and converting CV→kW at 0.7355 to compute a tax
would bake an undocumented assumption into a legal figure.

**Therefore: add an explicit `power_kw` column rather than converting.** Specs
without `power_kw` yield no tax estimate — consistent with how this codebase
already treats missing data (see the `missing_*` exclusion reasons in
`scoring.py:117-145`, and `_monthly_energy_cost` returning `None` when
consumption is absent).

### Repo conventions to match

- **Migrations** are idempotent: `ADD COLUMN IF NOT EXISTS`,
  `CREATE INDEX IF NOT EXISTS`. Read `0004_curated_catalog.sql` for the house
  style. They are applied by `apps/api/scripts/migrate.py`, which records them
  in `drivewise_schema_migrations`.
- **Missing data yields `None`, never a guess.** Never default a tax to 0.
- **New numeric assumptions carry a version, a source, and an observation
  date**, as in `energy_prices.py`.
- **UI strings are Italian with correct accents.** Match
  `apps/web/src/views/ModelAnalysis.tsx`, which already does this.
- `AGENTS.md` is binding — read it first.

## Commands you will need

| Purpose        | Command                                                              | Expected on success              |
|----------------|----------------------------------------------------------------------|----------------------------------|
| Backend tests  | `uv run --frozen --project apps/api --extra dev pytest apps/api -q`  | `143 passed, 4 skipped` baseline |
| Backend lint   | `uv run --frozen --project apps/api --extra dev ruff check apps/api` | `All checks passed!`             |
| Frontend tests | `bun run test:web`                                                   | `52 passed (14)` baseline        |
| Frontend types | `bun run typecheck:web`                                              | exit 0                           |
| Catalog check  | `uv run --project apps/api python apps/api/scripts/import_catalog.py --path data/fixtures/catalog/catalog-v1.synthetic.json --check` | validation passes, no DB writes |

The 4 skipped backend tests need `TEST_DATABASE_URL` and stay skipped locally.
**Do not run `migrate.py`** — it writes to a real database. Migration SQL is
verified by the test suite's migration tests in CI.

## Scope

**In scope**:

- `apps/api/migrations/0005_spec_power_kw.sql` (create)
- `apps/api/app/services/advisor/ownership_taxes.py` (create)
- `apps/api/app/services/advisor/model_analysis.py`
- `apps/api/app/services/advisor/scoring.py` — **only** `_score_candidate`'s
  `evidence` dict and `_build_provenance`. Nothing else.
- `apps/api/app/schemas/advisor.py` — `ModelAnalysisCostSummary` only
- `apps/api/app/schemas/vehicles.py` — add `power_kw` to the spec model
- `apps/api/app/repositories/advisor.py` — add `s.power_kw` to the SELECT lists
  and row-mapping helpers. **Do not touch the WHERE clauses or the
  `count_excluded_candidates` CASE ladder.**
- `apps/api/app/repositories/vehicles.py` — same, SELECT lists only
- `apps/api/app/ingestion/catalog.py` — accept and persist `power_kw`
- `docs/catalog-v1.schema.json` — add `power_kw`
- `data/fixtures/catalog/catalog-v1.synthetic.json` — add `power_kw` to variants
- `apps/api/tests/test_advisor_scoring.py`, `test_model_analysis_api.py`,
  `test_catalog_import.py`, `test_migrations.py`
- New: `apps/api/tests/test_ownership_taxes.py`
- `apps/web/src/api/drivewise.ts`, `apps/web/src/views/ModelAnalysis.tsx`
- `docs/data-model.md`, `docs/catalog-import.md` (document `power_kw`)
- `plans/README.md` (status row only)

**Out of scope** (do NOT touch):

- `BASE_WEIGHTS`, `raw_scores`, `_price_score`, `_use_case_score`,
  `_space_score`, `_efficiency_score`, `SCORING_VERSION` — **no ranking
  change.** Scores must be byte-identical before and after this plan.
- `EXCLUSION_REASON_ORDER` and every `_exclusion_reason` branch. A spec with no
  `power_kw` must remain eligible; missing power is not an exclusion.
- `energy_prices.py` — read it as a pattern, do not edit it.
- Insurance (RCA) estimation. It depends on driver history and province, is not
  deterministic from spec data, and does not belong in this plan.
- Regional bollo variation and regional EV exemptions. Model the national
  baseline only and say so in the assumptions list.

## Git workflow

- Branch: `advisor/002-italian-ownership-taxes`
- Conventional Commits, matching `git log` style: e.g.
  `feat(api): add italian ownership tax estimates`.
- Do NOT push, open a PR, or merge.

## Steps

### Step 1: Add `power_kw` end to end (no tax logic yet)

1. Create `apps/api/migrations/0005_spec_power_kw.sql`:

   ```sql
   ALTER TABLE vehicle_specs
     ADD COLUMN IF NOT EXISTS power_kw numeric(6, 2);

   ALTER TABLE vehicle_specs
     ADD CONSTRAINT vehicle_specs_power_kw_check
       CHECK (power_kw IS NULL OR power_kw > 0);
   ```

   Match `0004`'s idempotent style. Do **not** backfill from `horsepower` — the
   unit is undeclared, which is the whole reason this column exists.

2. Add `power_kw: float | None = None` to the spec schema in
   `apps/api/app/schemas/vehicles.py`.

3. Add `s.power_kw` to the SELECT column lists and the `_model_analysis_spec` /
   `_candidate_from_row` mapping helpers in
   `apps/api/app/repositories/advisor.py`, and to the equivalent SELECTs in
   `apps/api/app/repositories/vehicles.py`. **SELECT lists and mappers only.**

4. Add `power_kw` to `docs/catalog-v1.schema.json` (same shape as
   `horsepower`, but `["number", "null"]`), teach
   `apps/api/app/ingestion/catalog.py` to read and persist it, and add a
   `power_kw` value to the variants in
   `data/fixtures/catalog/catalog-v1.synthetic.json`.

5. Add `power_kw` to the documented column list in `docs/data-model.md`, with an
   explicit note that `horsepower` is unit-undeclared legacy data and `power_kw`
   is the authoritative figure for tax computation.

**Verify**:
- `uv run --frozen --project apps/api --extra dev pytest apps/api -q` → `143 passed, 4 skipped`
- `uv run --project apps/api python apps/api/scripts/import_catalog.py --path data/fixtures/catalog/catalog-v1.synthetic.json --check` → passes
- `uv run --frozen --project apps/api --extra dev ruff check apps/api` → `All checks passed!`

### Step 2: Create the sourced tax module

Create `apps/api/app/services/advisor/ownership_taxes.py`, structured exactly
like `energy_prices.py`:

- A module docstring stating this is the single source of truth for Italian
  ownership-tax assumptions, and that values must not be edited without
  updating the source citation and version together.
- `OWNERSHIP_TAX_ASSUMPTION_VERSION = "it-tax-<YYYY-MM-DD>-v1"` using the
  observation date from your Step 0 rate table.
- `BOLLO_SOURCE_NAME`, `BOLLO_SOURCE_URL`, `IPT_SOURCE_NAME`, `IPT_SOURCE_URL`,
  `OWNERSHIP_TAXES_OBSERVED_AT` — all from the Step 0 table.
- The rate constants from the Step 0 table.
- `OWNERSHIP_TAX_ASSUMPTIONS: list[str]` — prose sentences with the numbers
  **interpolated from the constants**, not retyped as literals, so the prose
  cannot drift. Include one sentence stating that regional variation and
  regional EV exemptions are not modeled.
- `annual_road_tax_eur(*, power_kw: float | None, fuel_type: str, euro_emission_standard: str | None, vehicle_age_years: int) -> float | None`
  → returns `None` when any required input is missing.
- `transfer_tax_eur(*, power_kw: float | None, condition: str) -> float | None`
  → returns `None` for `condition == "new"` and when power is missing.

Pure functions, no I/O, no database access.

**Verify**: `uv run --frozen --project apps/api --extra dev ruff check apps/api`
→ `All checks passed!`

### Step 3: Unit-test the tax functions directly

Create `apps/api/tests/test_ownership_taxes.py`. Model its structure on
`apps/api/tests/test_advisor_scoring.py` (plain pytest functions, no fixtures
needed for pure functions).

Cover, at minimum:
- A petrol car below the kW threshold.
- A petrol car above the kW threshold (band boundary).
- Exactly at the threshold — assert which side it falls on, deliberately.
- A BEV inside its exemption window, and one past it.
- `power_kw=None` → `None`.
- `euro_emission_standard=None` → `None`.
- `transfer_tax_eur` with `condition="new"` → `None`; with `"used"` → a value.

Expected values come from the Step 0 rate table. Write them as explicit literals
with a comment showing the arithmetic, e.g.
`# 51 kW * 2.58 EUR/kW = 131.58`.

**Verify**: `uv run --frozen --project apps/api --extra dev pytest apps/api/tests/test_ownership_taxes.py -q`
→ all pass.

### Step 4: Surface the taxes in model analysis

1. Extend `ModelAnalysisCostSummary` in `apps/api/app/schemas/advisor.py` with
   `estimated_annual_road_tax_eur: float | None = None` and
   `estimated_transfer_tax_eur: float | None = None`. Keep every existing field
   and its default.
2. In `model_analysis.py`'s `_estimate_costs`, call the Step 2 functions and
   populate the new fields. Gate them behind the existing `include_tco` flag,
   the same way `estimated_monthly_energy_eur` and
   `estimated_depreciation_3y_eur` already are. Derive `vehicle_age_years` from
   the analysis year that `_resolve_analysis_year` already computes — do not
   reintroduce a hardcoded year.
3. Append the `OWNERSHIP_TAX_ASSUMPTIONS` sentences to the `assumptions` list in
   `build_model_analysis`.
4. When `include_tco` is set but `power_kw` is missing, append `"power_kw"` to
   `missing_data` and a `"road_tax_not_estimated"` note, mirroring how the
   existing code handles absent energy consumption.

**Verify**: `uv run --frozen --project apps/api --extra dev pytest apps/api -q`
→ all pass (update `test_model_analysis_api.py` assertions that compare whole
cost-summary dicts).

### Step 5: Add bollo to advisor item evidence — without changing scores

In `scoring.py`'s `_score_candidate`, add the annual bollo to the `evidence`
dict, following the existing conditional-key style:

```python
if annual_road_tax is not None:
    evidence["annual_road_tax_eur"] = round(annual_road_tax, 2)
```

Also append a bollo-rate provenance entry in `_build_provenance`, exactly as
the energy-rate entry is appended there today.

**Do not** add it to `raw_scores`, `BASE_WEIGHTS`, `component_scores`, or any
factor message.

**Verify**: `uv run --frozen --project apps/api --extra dev pytest apps/api -q`
→ all pass. Critically, **no test asserting a `score` or `component_scores`
value may need changing.** If one does, you have altered ranking — revert and
re-read the "Deliberate scope limit" section.

### Step 6: Render the new costs

1. In `apps/web/src/api/drivewise.ts`, add the two fields to the
   `ModelAnalysisCostSummary` TypeScript interface (`number | null`).
2. In `apps/web/src/views/ModelAnalysis.tsx`, render them alongside the existing
   cost rows, with Italian labels and correct accents — e.g. `Bollo annuo` and
   `IPT (passaggio di proprietà)`. Reuse the existing currency formatter and
   the existing "not available" handling for `null` in that file; do not
   introduce a new formatter.
3. Add one assertion to `apps/web/src/views/ModelAnalysis.test.tsx` that the
   road-tax row renders when the value is present.

**Verify**: `bun run test:web` → `53 passed (14)`, and
`bun run typecheck:web` → exit 0.

## Test plan

| Test | File | Case |
|---|---|---|
| Tax bands, boundary, BEV, missing inputs | `apps/api/tests/test_ownership_taxes.py` (new) | 7 cases from Step 3 |
| Cost summary includes taxes under `tco` | `apps/api/tests/test_model_analysis_api.py` | new fields populated |
| Missing `power_kw` degrades cleanly | `apps/api/tests/test_model_analysis_api.py` | `None` + `missing_data` entry |
| Scores unchanged | `apps/api/tests/test_advisor_scoring.py` | existing assertions pass untouched |
| Evidence carries bollo | `apps/api/tests/test_advisor_scoring.py` | `evidence["annual_road_tax_eur"]` present |
| `power_kw` imports | `apps/api/tests/test_catalog_import.py` | round-trips from fixture |
| Migration applies | `apps/api/tests/test_migrations.py` | follow existing patterns there |
| Road-tax row renders | `apps/web/src/views/ModelAnalysis.test.tsx` | label + value visible |

## Done criteria

ALL must hold:

- [ ] Step 0's rate table was supplied and every constant in
      `ownership_taxes.py` traces to it with a source name, URL, and date
- [ ] `uv run --frozen --project apps/api --extra dev pytest apps/api -q` → all pass, ≥7 new tests
- [ ] `uv run --frozen --project apps/api --extra dev ruff check apps/api` → `All checks passed!`
- [ ] `bun run test:web` → `53 passed (14)`; `bun run typecheck:web` → exit 0
- [ ] `git diff apps/api/tests/test_advisor_scoring.py` shows **no changed
      score or `component_scores` expectation**
- [ ] `grep -n "SCORING_VERSION" apps/api/app/services/advisor/scoring.py` shows
      the value is still `"advisor-v2.0"`
- [ ] `grep -rn "0.7355\|horsepower \* \|/ 1.36" apps/api/app/` returns nothing
      (no CV→kW conversion was smuggled in)
- [ ] `import_catalog.py --check` passes on the synthetic fixture
- [ ] `plans/README.md` status row for 002 updated

## STOP conditions

Stop and report back — do not improvise — if:

- **Step 0's rate table was not supplied.** Do not proceed on guessed rates.
- The code at any location in "Current state" does not match the excerpt.
- Any existing test asserting a `score` or `component_scores` value fails. That
  means ranking moved, which this plan forbids.
- You conclude the tax cannot be computed without converting `horsepower` to kW.
  Report it; do not add the conversion.
- Computing bollo appears to require a region the request does not carry. The
  national baseline is the intended scope; if the supplied rate table has no
  usable national baseline, that is a blocking input problem to report.
- Any verification fails twice after a reasonable fix attempt.

## Maintenance notes

- **`ownership_taxes.py` values expire.** Rates change by finance law. The
  version constant and observation date exist so a reviewer can tell at a glance
  whether the figures are stale. Treat a stale date as a bug.
- **The deferred decision**: whether bollo enters the `running_cost` score
  component. Doing so requires bumping `SCORING_VERSION` to `advisor-v2.1`,
  updating `build_assumptions`, and rewriting score expectations across
  `test_advisor_scoring.py`. It is a deliberate follow-up, not an oversight.
- `power_kw` will be null for all pre-existing rows. Real catalog imports must
  start supplying it; until then model analysis reports no road tax for those
  specs. Consider whether the catalog importer should *require* `power_kw` for
  new variants once real inventory exists.
- A reviewer should scrutinize: that no exclusion reason was added for missing
  power, that prose assumptions interpolate rather than retype the constants,
  and that the migration is idempotent.
