# Plan 005: Qualify and pilot one real Italian catalog source

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. This plan contains an explicit operator-approval gate: reaching
> that gate is not authorization to continue. If anything in the "STOP
> conditions" section occurs, stop and report — do not improvise. When done,
> update the status row for this plan in `plans/README.md` — unless a reviewer
> dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 70bfe86..HEAD -- docs/source-review.md docs/source-pilot.md docs/source-pilot-report.md data/private/catalog apps/api/scripts/catalog_status.py apps/api/scripts/import_catalog.py docs/catalog-v1.schema.json`
>
> **IMPORTANT — this repo has a dirty working tree.** This plan was written
> against the working tree at commit `70bfe86`, which has extensive uncommitted
> changes. A diff against that SHA is not enough to detect drift. Confirm every
> "Current state" excerpt and the dependency artifacts before proceeding.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (source rights and real market data require human approval)
- **Depends on**: `plans/003-rankable-inventory-pipeline.md`
- **Category**: direction
- **Planned at**: commit `70bfe86`, 2026-07-31

## Why this matters

Drivewise can validate and transactionally import reviewed catalog snapshots,
but its committed catalog is synthetic and therefore proves only the pipeline.
The product cannot claim trustworthy Italian-market recommendations until at
least one real source has been assessed for storage, derived ranking,
attribution, freshness, and exact-variant pairing.

This is a risk-reduction pilot, not a crawler project. A valid outcome may be
`permitted`, `manual_validation_only`, or `not_permitted`. Rejecting an
unsuitable source with a documented reason is a successful pilot; silently
ranking it is not.

## Current state

### Dependency artifacts that must exist first

Plan 003 creates:

- `docs/source-review.md` — the human review checklist for source identity,
  licence/terms, ranking permission, supported metrics, attribution, automated
  access, freshness, reviewer, and decision rationale.
- `apps/api/scripts/catalog_status.py` — a read-only inventory report covering
  rankable counts, exclusion reasons, body/fuel/condition coverage, price
  range, and blind spots.
- A larger fictional catalog used only for deterministic coverage tests.

If `plans/README.md` does not mark Plan 003 `DONE`, or either dependency file is
missing, stop. Do not recreate a partial substitute inside this plan.

### Existing trust model

`docs/data-model.md:91-108`:

```markdown
`source_key` is the stable import identity and `market` records the source's
market scope. `ranking_permission` is an explicit trust decision with values
`permitted`, `not_permitted`, or `manual_validation_only`; only `permitted`
sources can contribute offers or metric evidence to rankings. URL, licence, and
notes retain the review basis.

Real Firecrawl source rows are intentionally excluded until crawling is
implemented.
```

`docs/catalog-import.md` establishes these constraints:

- Imports are reviewed JSON snapshots and make no external calls.
- Only `permitted` sources can contribute offers or metrics to Advisor
  rankings.
- Provenance claims name their exact URL, observation time, and
  `supported_metrics`.
- Real snapshots belong under `data/private/catalog/`, which is ignored.
- Only synthetic fixtures may be committed unless redistribution rights were
  reviewed.

`.gitignore` already contains:

```gitignore
data/private/
```

Do not weaken or remove that rule.

### Existing importer boundary

`apps/api/scripts/import_catalog.py` supports exactly:

```text
--path <json> --check
--path <json> --write
```

`--check` validates without a database. `--write` validates first, then imports
transactionally. On validation or database failure it emits a sanitized error
and exits non-zero. Reuse it unchanged.

The catalog model in `apps/api/app/ingestion/catalog.py` requires:

- Explicit source `ranking_permission`.
- Stable `source_key`, `canonical_key`, `model_family_key`, `variant_key`, and
  `listing_ref`.
- Exact variant↔vehicle and offer↔variant references.
- Source URL and observation time.
- Provenance claims that name only populated supported metrics.

### Product decision for this pilot

The pilot evaluates **one source for one declared role**, for example:

- offer identity, price, mileage, condition, location, and freshness; or
- homologation/specification metrics; or
- both, only if the reviewed terms and actual data support both.

Do not assume one source can support every metric required by Advisor. If other
evidence is required to produce a rankable offer, report that as a source-stack
gap instead of inventing or copying unsupported values.

### Repo conventions to match

- Documentation: concise Markdown, relative paths, no credentials or copied
  private datasets.
- Catalog files: strict v1 JSON matching `docs/catalog-v1.schema.json`.
- Source permission is fail-closed. Until approved, use
  `manual_validation_only` or `not_permitted`, never `permitted`.
- No source data, access token, cookie, API key, database URL, or private terms
  document may enter Git.
- No Firecrawl, automated scraping, browser automation against the candidate
  source, or new HTTP client is authorized by this plan.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Dependency status | `rg -n "\\| 003 \\|.*\\| DONE \\|" plans/README.md` | one match |
| Dependency files | `test -f docs/source-review.md && test -f apps/api/scripts/catalog_status.py` | exit 0 |
| Private-data ignore | `git check-ignore data/private/catalog/pilot-italy.json` | prints the path |
| Snapshot validation | `uv run --project apps/api python apps/api/scripts/import_catalog.py --path data/private/catalog/pilot-italy.json --check` | `Catalog is valid.`, exit 0 |
| Backend lint | `uv run --frozen --project apps/api --extra dev ruff check apps/api` | `All checks passed!` |
| Backend tests | `uv run --frozen --project apps/api --extra dev pytest apps/api -q` | all pass |
| Diff hygiene | `git diff --check -- docs/source-pilot.md docs/source-pilot-report.md` | exit 0 |

Database write and `catalog_status.py` commands require a disposable
pgvector-compatible PostgreSQL database. Never point the pilot at production or
the maintainer's normal development database.

## Suggested executor toolkit

- Use a browser or web-search capability only for **read-only research** into
  official source pages, terms, licence documents, and attribution rules.
- Prefer the source operator's own legal/terms/licence pages and official
  government or dataset documentation over blogs or summaries.
- Record URLs and access dates; do not quote large sections of copyrighted
  terms.

## Scope

**In scope**:

- `docs/source-pilot.md` (create; candidate matrix and operator decision)
- `docs/source-pilot-report.md` (create only after the disposable import)
- `data/private/catalog/pilot-italy.json` (local ignored working file; never
  commit)
- `plans/README.md` (status row only)

**Conditionally in scope only if redistribution is explicitly approved**:

- A separate sanitized or redistributable fixture path chosen by the operator.
  Stop and obtain the exact path and permission before creating it.

**Out of scope**:

- `apps/api/app/`, `apps/api/migrations/`, and scoring/repository logic
- `apps/api/scripts/import_catalog.py` and `catalog_status.py`
- Committed real listings or private source snapshots
- Firecrawl, scraping, automated browser collection, provider SDKs, scheduled
  jobs, or background ingestion
- Authentication, Redis, deployment, price-history tables, and alerts
- Changing eligibility rules to make the pilot rank
- Contacting a source owner, accepting terms, buying a licence, or creating an
  external account without the operator's separate authorization

## Git workflow

- Branch: `advisor/005-real-italian-source-pilot`
- Suggested commits:
  - `docs: assess Italian catalog source pilot`
  - `docs: record catalog source pilot outcome`
- The ignored `data/private/catalog/pilot-italy.json` must never be staged.
- Do not push, open a PR, or merge unless the operator explicitly asks.

## Steps

### Step 0: Confirm Plan 003 is complete

Run:

```bash
rg -n "\| 003 \|.*\| DONE \|" plans/README.md
test -f docs/source-review.md
test -f apps/api/scripts/catalog_status.py
```

Expected: all three commands succeed.

Then inspect:

```bash
uv run --project apps/api python apps/api/scripts/catalog_status.py --help
```

Expected: usage text and exit 0.

If Plan 003 is not done, stop. Its source checklist and inventory gauge are
prerequisites, not optional conveniences.

### Step 1: Research exactly three candidate sources

Create `docs/source-pilot.md`. Start it with:

```markdown
# Real Italian catalog source pilot

Status: RESEARCH
Decision owner: maintainer
Decision date: pending
Approved source key: pending
Approved ranking permission: pending
```

Add a comparison table with exactly these columns:

```text
Candidate | Official URL | Data role | Market coverage | Access method |
Terms/licence URL | Snapshot storage allowed | Derived ranking allowed |
Attribution required | Automated access position | Freshness | Main gap |
Provisional permission
```

Research exactly three plausible candidates. For each:

1. Use the operator's official product/data page.
2. Locate the official terms, licence, or dataset documentation.
3. Record the date reviewed.
4. Separate what is explicit from what is unknown.
5. Set provisional permission:
   - `permitted` only when stored snapshots and derived rankings are explicitly
     allowed;
   - `manual_validation_only` when manual evaluation is possible but ranking or
     redistribution is unclear;
   - `not_permitted` when terms prohibit the intended use.
6. Name the exact data role the source could support. Do not write "all data".

Do not copy listing data during this step.

**Verify**:

```bash
rg -n "^Status: RESEARCH$|^Decision owner: maintainer$|^Approved source key: pending$" docs/source-pilot.md
```

Expected: all three markers exist.

### Step 2: Present the recommendation and stop for approval

Under `## Recommendation`, write:

- The recommended candidate and role.
- The proposed `source_key`.
- Proposed `ranking_permission`.
- What exact fields/metrics it may support.
- Required attribution.
- Freshness/re-observation expectation.
- Any unanswered rights question.
- Why the other two candidates were not selected.

Then add this approval block:

```markdown
## Operator decision

- Decision: PENDING
- Source key: PENDING
- Ranking permission: PENDING
- Approved data role: PENDING
- Approved by: PENDING
- Decision date: PENDING
- Notes: PENDING
```

**STOP HERE.** Report the recommendation to the operator. Do not create the
private snapshot and do not change `Decision: PENDING` yourself.

Continuation is authorized only when the operator explicitly supplies the
decision and approves the source role and ranking permission. The operator may
approve `manual_validation_only`; that is a valid pilot decision.

### Step 3: Create a small ignored snapshot after approval

After approval, update the decision block with the operator's decision. Do not
invent their name or wording.

Create `data/private/catalog/pilot-italy.json` and confirm it is ignored before
adding data:

```bash
git check-ignore data/private/catalog/pilot-italy.json
```

Expected: the path is printed.

Build a small v1 snapshot with:

- Exactly one approved source record for the pilot candidate.
- 3–5 vehicle families.
- At least 5 exact variants.
- 6–12 offers when the source role includes offers.
- Both `new` and `used` only if the source actually contains both; never
  manufacture condition coverage.
- Stable keys and exact source URLs.
- Observation timestamps from the actual review.
- Only fields the source genuinely supports.
- Provenance claims restricted to those supported fields.
- The operator-approved `ranking_permission`.

If the source supports offers but not enough specification metrics for Advisor,
do not backfill guessed values. Let validation/status expose the gap.

Validate:

```bash
uv run --project apps/api python apps/api/scripts/import_catalog.py \
  --path data/private/catalog/pilot-italy.json \
  --check
```

Expected: `Catalog is valid.` and exit 0.

Then verify it remains untracked:

```bash
git status --short -- data/private/catalog/pilot-italy.json
```

Expected: no output.

### Step 4: Import only into a disposable database

Use a fresh disposable pgvector-compatible PostgreSQL database. Set
`DATABASE_URL` only in the local shell or local ignored `.env`; never write it
into a tracked file or plan.

Apply migrations:

```bash
uv run --project apps/api python apps/api/scripts/migrate.py
```

Expected: migrations apply or report already applied, exit 0.

Capture the baseline:

```bash
uv run --project apps/api python apps/api/scripts/catalog_status.py
```

Expected: exit 0. Save the aggregate counts locally; do not copy private rows.

Import:

```bash
uv run --project apps/api python apps/api/scripts/import_catalog.py \
  --path data/private/catalog/pilot-italy.json \
  --write
```

Expected: `Import status: completed`, sanitized counts, exit 0.

Rerun the identical import:

```bash
uv run --project apps/api python apps/api/scripts/import_catalog.py \
  --path data/private/catalog/pilot-italy.json \
  --write
```

Expected: `Import status: unchanged`, proving idempotency.

Run the status report again at a pinned `--as-of` within the snapshot freshness
window. Record:

- Total imported and rankable offers.
- Exclusions by reason.
- Coverage contributed by the source.
- Whether exact variant pairing held.
- Whether every ranking metric has permitted current provenance.

Do not change scoring or eligibility code if offers are excluded.

### Step 5: Publish only a sanitized pilot report

Create `docs/source-pilot-report.md` with:

- Approved source name/key and public URLs.
- Decision and reviewed data role.
- Date and disposable environment statement.
- Aggregate imported/rankable/excluded counts.
- Exclusion reasons without private row content.
- Exact-variant pairing result.
- Provenance/permission result.
- Attribution requirement.
- Freshness/re-observation requirement.
- Final verdict:
  - `GO`: suitable for the approved role;
  - `LIMITED`: import/review only, not ranking;
  - `NO-GO`: unsuitable.
- Next smallest action.

The report must not include copied listings, private URLs, credentials,
database identifiers, raw payloads, or personal data.

Update the first line of `docs/source-pilot.md` from `Status: RESEARCH` to
`Status: COMPLETE — GO`, `Status: COMPLETE — LIMITED`, or
`Status: COMPLETE — NO-GO`, matching the report verdict.

**Verify**:

```bash
git diff --check -- docs/source-pilot.md docs/source-pilot-report.md
git status --short -- data/private/catalog
```

Expected:

- Diff check exits 0.
- No private catalog file appears in status.

Run the unchanged code gates:

```bash
uv run --frozen --project apps/api --extra dev ruff check apps/api
uv run --frozen --project apps/api --extra dev pytest apps/api -q
```

Expected: lint and all tests pass. These commands prove the pilot did not
require runtime changes.

## Test plan

This is a product/data pilot. Its verification layers are:

1. **Rights review**: three-candidate matrix based on official pages.
2. **Human gate**: explicit operator decision before any source is marked
   `permitted`.
3. **Schema validation**: private snapshot passes `import_catalog.py --check`.
4. **Isolation**: write occurs only in a disposable database.
5. **Idempotency**: second identical import reports `unchanged`.
6. **Product readiness**: `catalog_status.py` reports rankable coverage or exact
   exclusion reasons.
7. **Regression**: backend lint and tests stay green without runtime edits.
8. **Privacy**: private snapshot remains ignored and untracked.

## Done criteria

- [ ] Plan 003 is `DONE`, and its source-review/status artifacts exist.
- [ ] Exactly three candidate sources were assessed from official material.
- [ ] The operator explicitly approved the chosen source, role, and
      `ranking_permission`.
- [ ] `pilot-italy.json` is ignored, untracked, and validates against catalog
      v1.
- [ ] The snapshot was imported only into a disposable database.
- [ ] A second identical import reports `unchanged`.
- [ ] `catalog_status.py` captured rankability/exclusion evidence.
- [ ] `docs/source-pilot-report.md` records a sanitized GO/LIMITED/NO-GO
      verdict.
- [ ] No scoring, eligibility, migration, crawler, or HTTP-client code changed.
- [ ] Backend lint and tests pass.
- [ ] `plans/README.md` status row for 005 is updated.

## STOP conditions

Stop and report back if:

- Plan 003 is not `DONE` or its required artifacts are missing.
- No candidate has official terms/licence material sufficient to assess
  snapshot storage and derived ranking.
- The operator has not explicitly approved the source role and permission.
- Approval would require accepting terms, purchasing access, contacting a
  source owner, or creating an external account.
- A source requires credentials, cookies, or secrets not already provisioned
  securely outside Git.
- The only way to make pilot offers rank is to edit scoring, eligibility SQL,
  migrations, or provenance rules.
- A disposable pgvector database is unavailable.
- The importer rejects the source data and satisfying the schema would require
  guessed or unsupported values.
- Any private source file appears in `git status`.
- Any verification fails twice after a reasonable correction.

## Maintenance notes

- Source permission is role-specific. Approval for listing prices does not
  automatically permit specification, reliability, review, or resale claims.
- Terms and licences can change. Record review dates and re-review before
  automating ingestion or expanding distribution.
- A GO verdict authorizes only the documented pilot role. Firecrawl,
  scheduled refresh, and production ingestion remain separate decisions.
- If the result is LIMITED or NO-GO, preserve the report; it prevents the same
  unsuitable source from being re-proposed without new evidence.
