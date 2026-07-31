# Plan 001: Make advisor recommendation runs retrievable and shareable by URL

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat 70bfe86..HEAD -- apps/api/app/api/routers/advisor.py apps/api/app/repositories/advisor.py apps/api/app/schemas/advisor.py apps/web/src/api/drivewise.ts apps/web/src/views/Advisor.tsx`
>
> **IMPORTANT — this repo has a dirty working tree.** This plan was written
> against the *working tree* at commit `70bfe86`, which has extensive
> uncommitted changes. A clean `git diff` against `70bfe86` will therefore be
> misleading. Trust the "Current state" excerpts below over the diff: read each
> cited file and confirm the excerpt matches what is on disk. Treat a mismatch
> as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `70bfe86`, 2026-07-26

## Why this matters

`POST /advisor/recommendations` already persists everything about a run — the
request payload, scoring version, assumptions, exclusion counts, and a full
per-item score breakdown — across the `recommendation_runs` and
`recommendation_items` tables. Nothing ever reads those rows back. The advisor
router exposes exactly two endpoints, both `POST`, so the run is write-only: a
user gets an answer, navigates away, and it is gone.

Buying a car is a decision that takes weeks and usually involves a second
person. An answer you cannot revisit or send to someone else is worth a
fraction of one you can. This plan adds a `GET` endpoint and a web route so a
run becomes a durable, linkable artifact — and it does so using storage that is
already being written today.

## Current state

### Files in play

- `apps/api/app/repositories/advisor.py` — `AdvisorRepository`. `create_run`
  (~line 507), `save_items` (~line 538), `mark_run_completed` (~line 593). No
  read method for runs exists.
- `apps/api/app/api/routers/advisor.py` — the advisor router. 109 lines, two
  POST endpoints, no GET.
- `apps/api/app/schemas/advisor.py` — Pydantic models, including
  `AdvisorRecommendationResponse` (~line 233).
- `apps/web/src/api/drivewise.ts` — the web API client.
- `apps/web/src/views/Advisor.tsx` — 729-line page component; the form and the
  results rendering are both inline in it.

### The response model that a retrieved run must reproduce

`apps/api/app/schemas/advisor.py:216-238`:

```python
class AdvisorRecommendationItem(BaseModel):
    vehicle: AdvisorVehicleSummary
    selected_spec: AdvisorSelectedSpec
    offer: AdvisorOffer
    score: float
    component_scores: dict[AdvisorScoreComponent, float]
    positive_factors: list[AdvisorFactor]
    tradeoffs: list[AdvisorFactor]
    evidence: dict[str, Any]
    provenance: list[AdvisorMetricProvenance]


class AdvisorRecommendationGroup(BaseModel):
    condition: Literal["new", "used"]
    items: list[AdvisorRecommendationItem]


class AdvisorRecommendationResponse(BaseModel):
    run_id: UUID
    scoring_version: str
    assumptions: list[str]
    excluded_counts_by_reason: dict[str, int]
    groups: list[AdvisorRecommendationGroup]
```

### What is persisted today, and the gap

`apps/api/app/repositories/advisor.py:538-591` (`save_items`) builds this
breakdown per item:

```python
breakdown = {
    "condition_group": condition_group,
    "component_scores": item.component_scores,
    "positive_factors": [
        factor.model_dump(mode="json") for factor in item.positive_factors
    ],
    "tradeoffs": [
        factor.model_dump(mode="json") for factor in item.tradeoffs
    ],
    "evidence": item.evidence,
}
```

It then inserts `vehicle_id`, `listing_id`, `spec_id`, `condition_group`,
`rank`, `score`, `rationale`, `scoring_version`, and `Jsonb(breakdown)`.

**The gap**: `vehicle`, `selected_spec`, `offer`, and `provenance` are not
persisted — only the foreign keys are. So a retrieved run cannot reproduce
`AdvisorRecommendationItem` without joining live `vehicles` / `vehicle_specs` /
`listings` / `vehicle_spec_provenance` rows.

**Design decision this plan commits to — read this before writing code.** Do
NOT reconstruct items by joining the live tables. Instead, extend the persisted
`score_breakdown` to contain a complete snapshot of the item. Reasons:

1. **Correctness.** Offers change: prices move, `is_active` flips, listings
   expire, provenance claims are superseded by newer imports (see
   `docs/catalog-import.md`). A run is a statement about the world at
   `evaluated_at`. Joining live rows would silently rewrite history and could
   show a €17,500 recommendation at a different price with the original score.
2. **Simplicity.** The GET becomes two indexed primary-key reads with zero
   joins, instead of duplicating the 200-line candidate join in
   `list_candidates`.
3. **No migration needed.** `score_breakdown` is already
   `jsonb NOT NULL DEFAULT '{}'::jsonb` (added in
   `apps/api/migrations/0004_curated_catalog.sql:284`).

The storage duplication is irrelevant at this scale and is the standard
trade-off for an immutable audit record.

### Relevant DDL (already applied — do not write a migration)

`apps/api/migrations/0002_create_mvp_schema.sql:92-101` and
`apps/api/migrations/0004_curated_catalog.sql:305-307`:

```sql
CREATE TABLE IF NOT EXISTS recommendation_runs (
  id uuid PRIMARY KEY,
  request_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'queued' CHECK (
    status IN ('queued', 'completed', 'failed')
  ),
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);
-- 0004 adds: scoring_version text, assumptions jsonb, exclusion_counts jsonb
```

`recommendation_items` has `run_id`, `vehicle_id`, `listing_id`, `spec_id`,
`condition_group` (`'new' | 'used' | 'legacy'`), `rank`, `score`, `rationale`,
`scoring_version`, `score_breakdown jsonb`, with unique indexes on
`(run_id, condition_group, vehicle_id)` and `(run_id, condition_group, rank)`.

### Repo conventions to match

- **Repository methods** take/return plain `dict`/`list` and use
  `self.conn.execute(...)` with `%s` placeholders — never f-string SQL. Rows come
  back dict-like (`row["column"]`). See `AdvisorRepository.list_candidates`.
- **Routers** use `Annotated[X, Depends(...)]` for every dependency. Existing
  dependency providers live in `apps/api/app/api/dependencies.py`; reuse
  `get_advisor_repository`. Do not add a new provider.
- **404s** are raised as `HTTPException(status_code=404, detail="...")`. See
  `apps/api/app/api/routers/vehicles.py` for the existing shape and copy its
  wording style.
- **Web routes** use TanStack file routes with a loader, plus the shared
  pending/error components. Exemplar —
  `apps/web/src/routes/vehicles_.$vehicleId.tsx` in full:

  ```tsx
  import { createFileRoute } from '@tanstack/react-router'

  import { fetchVehicle } from '../api/drivewise'
  import { VehicleDetailPage } from '../views/VehicleDetail'
  import { DataRouteError, DataRoutePending } from './-dataStates'
  import { loadDetail } from './-detailLoader'

  export const Route = createFileRoute('/vehicles_/$vehicleId')({
    loader: ({ params }) => loadDetail(() => fetchVehicle(params.vehicleId)),
    pendingComponent: DataRoutePending,
    errorComponent: DataRouteError,
    component: VehicleDetailRoute,
  })

  function VehicleDetailRoute() {
    return <VehicleDetailPage vehicle={Route.useLoaderData()} />
  }
  ```

  `loadDetail` (`apps/web/src/routes/-detailLoader.ts`) converts an API 404 into
  a router `notFound()`. Use it.
- **UI language is Italian.** All user-facing strings you add must be Italian,
  **with correct accents** (`è`, `più`, `città`). Match
  `apps/web/src/views/ModelAnalysis.tsx`, which does this correctly.
- `AGENTS.md` at the repo root is binding — read it first. Notably: keep
  dependencies minimal (this plan needs **no** new dependency), add tests for
  new runtime behavior, and never claim a check passes without fresh output.

## Commands you will need

| Purpose         | Command                                                                 | Expected on success              |
|-----------------|-------------------------------------------------------------------------|----------------------------------|
| Backend tests   | `uv run --frozen --project apps/api --extra dev pytest apps/api -q`     | `143 passed, 4 skipped` baseline |
| Backend lint    | `uv run --frozen --project apps/api --extra dev ruff check apps/api`    | `All checks passed!`             |
| Frontend tests  | `bun run test:web`                                                      | `52 passed (14)` baseline        |
| Frontend types  | `bun run typecheck:web`                                                 | exit 0, no output                |
| Frontend build  | `bun run build:web`                                                     | exit 0                           |

Run all five from the repo root. The 4 skipped backend tests require
`TEST_DATABASE_URL` and are expected to stay skipped locally.

## Scope

**In scope** (the only files you may modify or create):

- `apps/api/app/repositories/advisor.py`
- `apps/api/app/api/routers/advisor.py`
- `apps/api/app/schemas/advisor.py` (only if a new model is genuinely needed)
- `apps/api/tests/test_advisor_api.py`
- `apps/web/src/api/drivewise.ts`
- `apps/web/src/views/Advisor.tsx`
- `apps/web/src/views/AdvisorResults.tsx` (create)
- `apps/web/src/routes/advisor_.$runId.tsx` (create)
- `apps/web/src/views/Advisor.test.tsx`
- `plans/README.md` (status row only)

**Out of scope** (do NOT touch, even though they look related):

- `apps/api/app/services/advisor/scoring.py` — the scoring algorithm must not
  change. This plan alters persistence and retrieval only; any score change
  means you have broken something.
- `apps/api/app/services/advisor/model_analysis.py` and
  `energy_prices.py` — unrelated, and another task may be editing them.
- `apps/api/migrations/` — **do not add a migration.** Every column needed
  already exists. If you believe you need one, that is a STOP condition.
- `apps/web/src/routeTree.gen.ts` — generated. It updates itself when the dev
  server or build runs. Never hand-edit it.
- Authentication or ownership of runs. Runs are unauthenticated and
  URL-guessable by design for now; a `run_id` is a v4 UUID. Do not add auth.

## Git workflow

- Branch: `advisor/001-retrievable-advisor-runs`
- Commit per step or logical unit. The repo uses Conventional Commits — recent
  examples from `git log`: `feat(web): persist collection filters in URLs`,
  `feat(api): add deterministic advisor with document evidence`,
  `fix: harden model analysis flow`.
- Do NOT push, open a PR, or merge.

## Steps

### Step 1: Persist a complete item snapshot in `score_breakdown`

In `apps/api/app/repositories/advisor.py`, in `save_items`, extend the
`breakdown` dict so it fully describes the item. Add these keys alongside the
existing ones:

- `"vehicle"`: `item.vehicle.model_dump(mode="json")`
- `"selected_spec"`: `item.selected_spec.model_dump(mode="json")`
- `"offer"`: `item.offer.model_dump(mode="json")`
- `"provenance"`: `[entry.model_dump(mode="json") for entry in item.provenance]`
- `"score"`: `item.score`

Use `mode="json"` everywhere so UUIDs, `date`, and `datetime` values serialize
to strings that `Jsonb` can store and Pydantic can re-validate on read. Keep
every existing key exactly as it is.

**Verify**: `uv run --frozen --project apps/api --extra dev pytest apps/api -q`
→ `143 passed, 4 skipped`. (No behavior is observable yet; this confirms you
broke nothing.)

### Step 2: Add a read method to `AdvisorRepository`

Add `get_run(self, run_id: UUID) -> dict[str, Any] | None`.

It must:

1. Select `id`, `scoring_version`, `assumptions`, `exclusion_counts`, `status`,
   `created_at`, `completed_at` from `recommendation_runs` where `id = %s`.
   Return `None` if there is no such row.
2. Select all `recommendation_items` for that `run_id`, ordered by
   `condition_group`, then `rank`.
3. Return a dict shaped `{"run": <run row as dict>, "items": [<item rows>]}`.

Two indexed queries, no joins to `vehicles` / `listings` / `vehicle_specs`.
Follow the `%s` placeholder convention; never interpolate the UUID into SQL.

**Verify**: `uv run --frozen --project apps/api --extra dev ruff check apps/api`
→ `All checks passed!`

### Step 3: Add `GET /advisor/runs/{run_id}`

In `apps/api/app/api/routers/advisor.py`, add:

```python
@router.get("/runs/{run_id}", response_model=AdvisorRecommendationResponse)
def read_recommendation_run(
    run_id: UUID,
    repository: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
) -> AdvisorRecommendationResponse:
    ...
```

Behavior:

- Unknown `run_id` → `HTTPException(status_code=404, ...)` with an Italian-free,
  English detail string matching the style used in
  `apps/api/app/api/routers/vehicles.py`.
- Reassemble groups from the stored items: group by the item's
  `condition_group`, ordered `new` before `used`, items ordered by `rank`.
  Build each `AdvisorRecommendationItem` from `score_breakdown` via
  `AdvisorRecommendationItem.model_validate(...)`.
- Skip any item whose `condition_group` is `'legacy'`. Legacy V1 rows predate
  the snapshot format and cannot be reconstructed; a run consisting only of
  legacy rows returns empty `groups`, not a 500.
- If an item's `score_breakdown` lacks the Step 1 keys (a run written before
  this plan landed), that item cannot be reconstructed. Omit it rather than
  raising. Do not attempt a live-table fallback.

**Verify**:
`uv run --frozen --project apps/api --extra dev pytest apps/api -q` →
`143 passed, 4 skipped`, then
`uv run --frozen --project apps/api --extra dev ruff check apps/api` →
`All checks passed!`

### Step 4: Backend tests

Add to `apps/api/tests/test_advisor_api.py`, following the existing fixture and
`app.dependency_overrides` style already used in that file (read the top 60
lines first; it builds fake repository objects rather than touching a database).

Cases:

1. **Round trip**: `POST /advisor/recommendations`, take the returned `run_id`,
   `GET /advisor/runs/{run_id}`, and assert the response body equals the POST
   response body. This is the central test — it proves retrieval is faithful.
2. **404**: `GET /advisor/runs/<random uuid4>` → status 404.
3. **Malformed id**: `GET /advisor/runs/not-a-uuid` → status 422 (FastAPI's
   path-type validation handles this; assert it rather than adding code).
4. **Legacy/incomplete item omitted**: a stored item whose `score_breakdown` is
   `{}` is skipped and the endpoint still returns 200.

**Verify**: `uv run --frozen --project apps/api --extra dev pytest apps/api -q`
→ `147 passed, 4 skipped` (143 + 4 new).

### Step 5: Add the client function

In `apps/web/src/api/drivewise.ts`, add:

```ts
export async function fetchAdvisorRun(
  runId: string,
): Promise<AdvisorRecommendationResponse>
```

Use the existing private `fetchJson` helper so 404s become `ApiResponseError`
with `status: 404` (which `isApiNotFoundError` and `loadDetail` rely on). The
mock-fallback second argument should throw
`new ApiResponseError('Advisor run not found', 404)` — do **not** invent a mock
run payload. Reason: the mock path already reimplements too much backend logic,
and a fabricated run would be indistinguishable from a real one in the UI.

**Verify**: `bun run typecheck:web` → exit 0.

### Step 6: Extract the results rendering out of `Advisor.tsx`

`apps/web/src/views/Advisor.tsx` currently renders the form *and* the results
in one 729-line component. Create
`apps/web/src/views/AdvisorResults.tsx` exporting:

```tsx
export function AdvisorResults({
  response,
}: {
  response: AdvisorRecommendationResponse
})
```

Move the results-rendering JSX and its helpers (the group/item/factor/
provenance/evidence rendering, the `Intl` formatters, the label maps) into it
unchanged. `Advisor.tsx` keeps the form and state and renders
`<AdvisorResults response={response} />` when it has a response.

This is a pure move. Do not restyle, do not rename CSS classes, do not change
markup structure — `Advisor.test.tsx` asserts on rendered text and must keep
passing without modification.

**Verify**: `bun run test:web` → `52 passed (14)`, unchanged. If any Advisor
test fails, you changed markup; revert and re-do the move faithfully.

### Step 7: Add the shareable run route

Create `apps/web/src/routes/advisor_.$runId.tsx`, modelled exactly on
`apps/web/src/routes/vehicles_.$vehicleId.tsx` (quoted in full in "Current
state"):

- `createFileRoute('/advisor_/$runId')`
- `loader: ({ params }) => loadDetail(() => fetchAdvisorRun(params.runId))`
- `pendingComponent: DataRoutePending`, `errorComponent: DataRouteError`
- component renders `<AdvisorResults response={Route.useLoaderData()} />`

The underscore suffix on `advisor_` matters: it opts the route out of nesting
under the `/advisor` layout, matching how `vehicles_.$vehicleId` relates to
`vehicles`. Getting this wrong renders the form above the results.

**Verify**: `bun run build:web` → exit 0 (this regenerates `routeTree.gen.ts`),
then `bun run typecheck:web` → exit 0.

### Step 8: Surface the link on the Advisor page

In `Advisor.tsx`, when a response is present, render a link to
`/advisor/{run_id}` so the user can copy it. Use TanStack `Link` (the repo uses
it for all internal navigation — see the existing import at the top of
`Advisor.tsx`). Italian label with correct accents, e.g.
`Link permanente a questo risultato`.

Add one test to `Advisor.test.tsx` asserting the link renders with the returned
`run_id` in its `href` after a successful submit. Model it on the existing
submit test in that file.

**Verify**: `bun run test:web` → `53 passed (14)`, and
`bun run typecheck:web` → exit 0.

## Test plan

| Test | File | Case |
|---|---|---|
| Round trip fidelity | `apps/api/tests/test_advisor_api.py` | POST then GET returns an identical body |
| Unknown run | `apps/api/tests/test_advisor_api.py` | 404 |
| Malformed run id | `apps/api/tests/test_advisor_api.py` | 422 |
| Incomplete breakdown | `apps/api/tests/test_advisor_api.py` | item omitted, 200 |
| Permalink rendered | `apps/web/src/views/Advisor.test.tsx` | link href contains `run_id` |

Structural patterns to follow: `apps/api/tests/test_advisor_api.py` for the
dependency-override style, `apps/api/tests/test_model_analysis_api.py` for
building fake rows, `apps/web/src/views/Advisor.test.tsx` for the submit flow.

Final totals: backend `147 passed, 4 skipped`; frontend `53 passed (14)`.

## Done criteria

ALL must hold:

- [ ] `uv run --frozen --project apps/api --extra dev pytest apps/api -q` → `147 passed, 4 skipped`
- [ ] `uv run --frozen --project apps/api --extra dev ruff check apps/api` → `All checks passed!`
- [ ] `bun run test:web` → `53 passed (14)`
- [ ] `bun run typecheck:web` → exit 0
- [ ] `bun run build:web` → exit 0
- [ ] `GET /advisor/runs/{run_id}` returns a body byte-identical to the originating POST response for a freshly created run
- [ ] `git diff --name-only` lists only files from the In-scope list (plus `routeTree.gen.ts`, which the build regenerates)
- [ ] `grep -rn "recommendation_runs" apps/api/migrations/` shows no new migration file was added
- [ ] `plans/README.md` status row for 001 updated

## STOP conditions

Stop and report back — do not improvise — if:

- The code at any location in "Current state" does not match the excerpt.
- You conclude a database migration is required. Every column this plan needs
  already exists; needing one means the plan's model of the schema is wrong.
- The round-trip test in Step 4 cannot be made to pass without changing
  anything under `apps/api/app/services/advisor/`. That would mean scoring
  output is not fully captured by the snapshot, which is a design problem to
  report, not to patch.
- Moving the results JSX in Step 6 breaks existing `Advisor.test.tsx`
  assertions and you cannot fix it by making the move more faithful.
- Any verification fails twice after a reasonable fix attempt.

## Maintenance notes

- **The snapshot is now a persistence contract.** If a field is added to
  `AdvisorRecommendationItem` in `schemas/advisor.py`, Step 1's breakdown must
  be extended too, or retrieved runs will silently lose it. A reviewer should
  check for this pairing on any future change to that model.
- Old runs created before this plan are not retrievable. That is accepted and
  handled by the omit-incomplete-items rule, not by backfill.
- Runs are unauthenticated and permanent. When auth arrives, decide whether a
  run gets an owner and whether these URLs should expire — the endpoint is the
  natural place to enforce it.
- Deliberately deferred: no pagination on items (max 5 per group by
  `MAX_ITEMS_PER_GROUP`), no run listing endpoint, no delete. Add them when
  there is a user to scope them to.
