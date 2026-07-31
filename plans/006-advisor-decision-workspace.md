# Plan 006: Add a shareable 2–3 offer decision workspace

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan in
> `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 70bfe86..HEAD -- apps/web/src/api/drivewise.ts apps/web/src/views/AdvisorResults.tsx apps/web/src/views/AdvisorComparison.tsx apps/web/src/views/AdvisorComparison.test.tsx apps/web/src/routes/advisor_.'$runId'.tsx apps/web/src/routes/advisor_.'$runId'.compare.tsx apps/web/src/routes/-advisorCompareSearch.ts apps/web/src/routes/-advisorCompareSearch.test.ts apps/web/src/router.test.ts apps/web/src/styles.css`
>
> **IMPORTANT — this plan depends on files that Plan 001 creates.** It was
> written against the dirty working tree at commit `70bfe86`, before Plan 001
> landed. Run the dependency check first. Once Plan 001 and Plan 003 are
> `DONE`, compare the expected post-dependency shapes in "Current state" with
> disk. Any mismatch is a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (adds a new cross-route selection and comparison flow)
- **Depends on**: `plans/001-retrievable-advisor-runs.md`,
  `plans/003-rankable-inventory-pipeline.md`
- **Category**: direction
- **Planned at**: commit `70bfe86`, 2026-07-31

## Why this matters

The Advisor explains one recommendation card at a time, while Model Analysis
returns suggested actions such as `compare_alternatives` and `open_checklist`
as inert labels. A buyer still has to remember differences across cards and
manually assemble the decision.

This plan closes that gap with a narrow workspace: select 2–3 offers from one
persisted Advisor run, compare their exact variants, prices, costs, component
scores, trade-offs, provenance, and uncertainty, then share or reload the URL.
It deliberately does not add accounts, saved shortlists, PDF reports, or new
scoring logic.

## Current state

### Dependency gate

Before starting, `plans/README.md` must mark both Plan 001 and Plan 003 `DONE`.

Plan 001 must have created:

- `GET /advisor/runs/{run_id}` returning the same
  `AdvisorRecommendationResponse` snapshot as the original POST.
- `fetchAdvisorRun(runId)` in `apps/web/src/api/drivewise.ts`.
- `apps/web/src/views/AdvisorResults.tsx`, extracted from the current
  `Advisor.tsx`.
- `apps/web/src/routes/advisor_.$runId.tsx`, whose loader renders a persisted
  run at `/advisor/{runId}`.

Plan 003 must have created a synthetic catalog broad enough to produce several
meaningful candidates across body styles, fuel types, primary uses, and new/
used groups.

If either dependency is missing, stop. Do not duplicate its implementation in
this plan.

### Existing response already contains comparison data

The current client contract in `apps/web/src/api/drivewise.ts:256-313` includes:

```ts
export interface AdvisorOffer {
  id: string
  vehicle_id: string
  spec_id: string
  source_id: string
  listing_ref: string
  title: string
  price_eur: number
  mileage: number | null
  condition: 'new' | 'used' | 'certified'
  location_region: string | null
  source_url: string | null
  listed_at: string | null
  last_seen_at?: string
  valid_until: string | null
  is_active: boolean
}

export interface AdvisorRecommendationItem {
  vehicle: VehicleSummary
  selected_spec: AdvisorSelectedSpec
  offer: AdvisorOffer
  score: number
  component_scores: Record<AdvisorScoreComponent, number>
  positive_factors: AdvisorFactor[]
  tradeoffs: AdvisorFactor[]
  evidence: Record<string, unknown>
  provenance: AdvisorMetricProvenance[]
}
```

No backend comparison endpoint is needed. The run snapshot is the comparison
boundary.

### Current results are card-by-card

`apps/web/src/views/Advisor.tsx:427-487` currently:

- Splits recommendations into `new` and `used`.
- Renders up to five cards per group.
- Shows offer facts, component scores, positive factors, trade-offs, evidence,
  and provenance inside each card.
- Provides no selection state or comparison action.

After Plan 001, this rendering lives in `AdvisorResults.tsx`; preserve its
existing information and CSS classes while adding selection affordances.

### Current next actions are inert

`apps/api/app/schemas/advisor.py:55-60` defines:

```python
NextAction = Literal[
    "modify_parameters",
    "open_checklist",
    "compare_alternatives",
    "generate_report",
]
```

`apps/web/src/views/ModelAnalysis.tsx:302-308` renders the values as list items:

```tsx
<ul className="next-actions" aria-label="Azioni suggerite">
  {response.next_actions.map((action) => (
    <li className="action-token" key={action}>
      {formatResultLabel(action)}
    </li>
  ))}
</ul>
```

This plan implements comparison from Advisor results. It does not modify Model
Analysis; wiring model-analysis actions requires a canonical run/candidate
relationship that does not exist yet.

### Product decisions fixed by this plan

1. **Same-run comparison only.** Every compared item must come from one
   persisted run so request constraints, scoring version, assumptions, and
   evaluation time are shared.
2. **Two required, three maximum.** Two is enough for a decision; three is the
   maximum before the matrix becomes unreadable on mobile.
3. **Offer ID is the URL identity.** Use `offer.id`, which uniquely identifies
   the exact listing within the run snapshot. Do not use array indexes, rank,
   vehicle ID, or mutable titles.
4. **URL is the saved state.** The route is
   `/advisor/{runId}/compare?offers=<id>,<id>[,<id>]`.
5. **Fail closed.** Unknown, duplicate, or malformed offer IDs are discarded.
   Fewer than two valid selections render guidance, not guessed fallbacks.
6. **No score recomputation.** Render the immutable stored response.
7. **Evidence stays visible.** A comparison that hides trade-offs, assumptions,
   provenance, or freshness violates the Drivewise trust model.

### Frontend conventions to match

- TanStack file routes own loader/search state.
- Route-level API loading uses `loadDetail` so API 404s reach the root
  not-found boundary.
- Search normalization is a small pure helper with direct unit tests, matching
  `apps/web/src/routes/-collectionSearch.ts`.
- User-facing copy is Italian with correct accents.
- Internal navigation uses TanStack `Link`.
- Use existing CSS variables/classes and native controls. Add no dependency.
- `routeTree.gen.ts` is generated by the build and must never be hand-edited.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Dependency check | `rg -n "\\| (001|003) \\|.*\\| DONE \\|" plans/README.md` | two matches |
| Frontend tests | `bun run test:web` | all tests pass |
| Frontend types | `bun run typecheck:web` | exit 0, no errors |
| Frontend build | `bun run build:web` | exit 0; route tree regenerates |
| Backend regression | `uv run --frozen --project apps/api --extra dev pytest apps/api -q` | all tests pass |
| Backend lint | `uv run --frozen --project apps/api --extra dev ruff check apps/api` | `All checks passed!` |
| Scope guard | `git diff --name-only` | only in-scope paths plus generated `routeTree.gen.ts` and plan status |
| Diff hygiene | `git diff --check` | exit 0, no output |

## Suggested executor toolkit

- Use the `tanstack-start-best-practices` skill if available when implementing
  route search validation and loader state.
- Use the shared T3 preview browser first for the final real-browser flow when
  available; otherwise use the repo's established Playwright/browser tooling.

## Scope

**In scope**:

- `apps/web/src/views/AdvisorResults.tsx`
- `apps/web/src/views/AdvisorComparison.tsx` (create)
- `apps/web/src/views/AdvisorComparison.test.tsx` (create)
- `apps/web/src/routes/advisor_.$runId.compare.tsx` (create)
- `apps/web/src/routes/-advisorCompareSearch.ts` (create)
- `apps/web/src/routes/-advisorCompareSearch.test.ts` (create)
- `apps/web/src/router.test.ts`
- `apps/web/src/styles.css`
- `apps/web/src/routeTree.gen.ts` (generated only; never hand-edit)
- `plans/README.md` (status row only)

**Conditionally in scope if Plan 001 places its tests elsewhere**:

- The existing test file that directly covers `AdvisorResults`. Use it only for
  selection/link tests; do not relocate unrelated tests.

**Out of scope**:

- All backend runtime files, schemas, repositories, routers, and migrations
- Advisor scoring, exclusions, weights, assumptions, or ranking order
- Model Analysis UI/runtime
- Authentication, ownership, saved lists, user profiles, database writes, or
  analytics
- Cross-run comparison
- Price history, alerts, report/PDF generation, dealer contact, or checkout
- Restyling the entire Advisor page
- More than three selected offers

## Git workflow

- Branch: `advisor/006-advisor-decision-workspace`
- Suggested logical commits:
  - `feat(web): add advisor comparison route`
  - `test(web): cover advisor decision workspace`
- Do not push, open a PR, or merge unless the operator explicitly asks.

## Steps

### Step 0: Verify dependencies and baseline

Run:

```bash
rg -n "\| (001|003) \|.*\| DONE \|" plans/README.md
test -f apps/web/src/views/AdvisorResults.tsx
test -f 'apps/web/src/routes/advisor_.$runId.tsx'
rg -n "fetchAdvisorRun" apps/web/src/api/drivewise.ts
```

Expected: two DONE rows and all file/symbol checks succeed.

Run the frontend baseline:

```bash
bun run test:web
bun run typecheck:web
bun run build:web
```

Expected: all pass before editing. Record actual test totals; do not rely on
the pre-dependency totals written in older plans.

### Step 1: Add pure comparison-search normalization

Create `apps/web/src/routes/-advisorCompareSearch.ts` exporting:

```ts
export interface AdvisorCompareSearch {
  offers?: string
}

export function normalizeAdvisorCompareSearch(
  search: Record<string, unknown>,
): AdvisorCompareSearch

export function selectedOfferIds(
  search: AdvisorCompareSearch,
): string[]
```

Behavior:

- Accept only a string `offers` value.
- Split on commas.
- Trim whitespace.
- Drop blank entries.
- Preserve first-seen order.
- Remove duplicates.
- Keep at most three IDs.
- Do not validate UUID syntax here. Tests and mock IDs may not be UUIDs, and
  membership in the loaded run is the authoritative check.
- Return `{}` when no IDs survive; otherwise return the normalized comma-joined
  string.

Create `-advisorCompareSearch.test.ts` covering:

1. Missing/non-string input → `{}` and `[]`.
2. Whitespace and blanks normalized.
3. Duplicates removed in first-seen order.
4. Four or more IDs truncated to three.
5. Empty result omits `offers`.

**Verify**:

```bash
bun run --cwd apps/web test -- src/routes/-advisorCompareSearch.test.ts
bun run typecheck:web
```

Expected: new tests pass and typecheck exits 0.

### Step 2: Create the comparison route

Create `apps/web/src/routes/advisor_.$runId.compare.tsx`.

It must:

- Use `createFileRoute('/advisor_/$runId/compare')`.
- Use `validateSearch: normalizeAdvisorCompareSearch`.
- Load the persisted run with
  `loadDetail(() => fetchAdvisorRun(params.runId))`.
- Reuse `DataRoutePending` and `DataRouteError`.
- Pass `Route.useLoaderData()` and `selectedOfferIds(Route.useSearch())` to
  `<AdvisorComparison />`.

After creating the route, run the build so TanStack regenerates the route tree:

```bash
bun run build:web
```

Expected: exit 0 and the generated route tree contains the literal path
`/advisor/$runId/compare`.

Verify without hand-editing:

```bash
rg -n '/advisor/\$runId/compare' apps/web/src/routeTree.gen.ts
```

Expected: at least one match.

### Step 3: Build the decision matrix

Create `apps/web/src/views/AdvisorComparison.tsx` with props:

```tsx
interface AdvisorComparisonProps {
  response: AdvisorRecommendationResponse
  requestedOfferIds: string[]
}
```

Flatten `response.groups` in their response order. Filter
`requestedOfferIds` against `item.offer.id`, preserve requested order, and
render at most three items.

#### Fewer than two valid items

Render:

- Heading `Confronta le alternative`.
- Guidance explaining that 2–3 offers from this same run are required.
- A TanStack link back to `/advisor/{run_id}` labelled
  `Torna ai risultati`.
- If unknown IDs were discarded, a neutral warning:
  `Una o più offerte non appartengono a questo risultato.`

Do not auto-select replacements.

#### Two or three valid items

Render:

- Page heading and shared run context:
  - scoring version;
  - assumptions;
  - exclusion counts only as a collapsed/secondary context, not one copy per
    item.
- One column/card per exact offer. Each must show:
  - make, model, model year, exact trim, body style, fuel type;
  - price, condition, mileage, location, and freshness date;
  - external source link when available;
  - total score;
  - all five component scores in fixed order;
  - strongest positive factor and strongest trade-off, defined as greatest
    absolute `contribution` within each respective list;
  - energy cost/consumption, range, seats, and cargo when present in evidence or
    selected spec;
  - provenance grouped by metric, retaining source URL and observation date;
  - a visible `Dati non disponibili` label for comparison rows missing on one
    or more items.
- A compact checklist section generated from existing evidence only:
  - verify offer is still active/current;
  - open the original source;
  - inspect the top trade-off;
  - verify any missing comparison metric.

The checklist is presentation, not persisted state. Do not invent vehicle-
specific mechanical claims.

#### Responsive behavior

- Desktop: 2–3 columns aligned by comparison sections.
- Narrow screens: horizontally scrollable columns or stacked cards with a
  sticky item heading; choose the smallest implementation consistent with the
  existing CSS.
- Do not shrink body text below the current app's normal text size.

**Verify**:

```bash
bun run typecheck:web
```

Expected: exit 0.

### Step 4: Add selection controls to persisted results

Modify `AdvisorResults.tsx` to support selecting offers for comparison.

Required behavior:

- Each recommendation card has a labelled checkbox or toggle:
  `Aggiungi al confronto`.
- Selection is keyed by `item.offer.id`.
- Maximum three. When three are selected, unselected controls are disabled and
  explanatory text says `Puoi confrontare al massimo 3 offerte.`
- A comparison action is visible when at least two are selected:
  `Confronta 2 offerte` / `Confronta 3 offerte`.
- The action is a TanStack `Link` to:

```text
/advisor/{response.run_id}/compare?offers=<ordered comma-separated offer ids>
```

- Selection order is the user's click order.
- Deselecting an offer removes it without reordering the remaining selections.
- The existing cards, factors, evidence, provenance, and permanent-run link
  remain visible.
- Do not put selection in local storage or a database. The comparison URL is
  the durable state.

If Plan 001 made `AdvisorResults` a server-rendered pure component without
client state, isolate selection into a small child component rather than
moving the whole result view back into `Advisor.tsx`.

**Verify**:

```bash
bun run test:web
bun run typecheck:web
```

Expected: all existing tests pass before new tests are added.

### Step 5: Add focused component tests

Create `apps/web/src/views/AdvisorComparison.test.tsx`. Reuse the existing
Advisor response fixture shape rather than creating a second incompatible
contract.

Cover:

1. Two valid offer IDs render two exact variants.
2. Requested order, not score/rank order, controls column order.
3. Unknown IDs are discarded and guidance appears when fewer than two remain.
4. Three IDs render; a fourth can never reach the component from normalized
   search, but defensively render only three.
5. Total/component scores, top trade-off, source, freshness, and at least one
   provenance entry are visible.
6. A metric missing from one item renders `Dati non disponibili`.
7. The back link points to the same run.

Add selection tests to the existing `AdvisorResults`/Advisor test file:

1. Comparison link absent with 0–1 selection.
2. Selecting two produces a link with ordered offer IDs.
3. Three is allowed; a fourth unselected control is disabled.
4. Deselecting preserves the relative order of remaining IDs.
5. Existing result explanation/provenance remains rendered.

**Verify**:

```bash
bun run test:web
```

Expected: all existing and new tests pass.

### Step 6: Add route-level tests

Extend `apps/web/src/router.test.ts`.

Cases:

1. Opening `/advisor/<run>/compare?offers=offer-a,offer-b` fetches exactly
   `/advisor/runs/<run>` and renders both offers without rendering the Advisor
   form route.
2. A run API 404 renders the root not-found page.
3. A malformed/empty search renders comparison guidance, not an exception.
4. Duplicates and a fourth ID are normalized.

Use `createMemoryHistory` and the real generated route tree, matching the
existing detail-route tests in that file.

**Verify**:

```bash
bun run test:web
bun run typecheck:web
bun run build:web
```

Expected: all pass.

### Step 7: Run a real full-stack browser smoke

Use a fresh disposable pgvector database. Complete Plan 003's catalog import,
then start the API and web app with CORS allowing both:

```text
http://localhost:3000
http://127.0.0.1:3000
```

Create an Advisor run that returns at least three offers. In a real browser:

1. Open `/advisor`.
2. Submit a scenario with at least three results.
3. Select two offers, including new/used when the result supports both.
4. Open the comparison.
5. Confirm exact variants, price, score, trade-off, source/freshness, and
   provenance appear.
6. Copy the comparison URL into a fresh navigation.
7. Confirm the same two offers and order restore from the URL.
8. Add a third offer and confirm a fourth cannot be selected.
9. Remove one `offers` ID or replace it with an unknown ID; confirm guidance
   appears rather than a substituted candidate.
10. Check one narrow/mobile viewport for readable comparison navigation.

Capture the final comparison URL and one screenshot as verification artifacts.
Do not commit screenshots unless the operator asks.

If no automation-capable shared browser or local runtime is available, stop and
report the missing capability. Do not call the plan complete on unit tests
alone.

### Step 8: Run final gates and scope check

Run:

```bash
bun run test:web
bun run typecheck:web
bun run build:web
uv run --frozen --project apps/api --extra dev ruff check apps/api
uv run --frozen --project apps/api --extra dev pytest apps/api -q
git diff --check
```

Expected: all pass.

Run:

```bash
git diff --name-only
```

Expected: only the in-scope frontend files, generated
`apps/web/src/routeTree.gen.ts`, and `plans/README.md`. Any backend runtime or
migration change is a plan violation.

## Test plan

| Layer | File | Cases |
|---|---|---|
| Search normalization | `-advisorCompareSearch.test.ts` | missing, blanks, dedupe, order, max 3 |
| Comparison component | `AdvisorComparison.test.tsx` | 2/3 items, requested order, unknown IDs, evidence, missing data |
| Selection interaction | existing Advisor results test | min 2, max 3, ordered URL, deselection |
| Real route tree | `router.test.ts` | loader URL, no parent form, 404, malformed search |
| Full-stack browser | uncommitted artifact | select, compare, reload URL, unknown ID, narrow viewport |
| Regression | existing suites | frontend and backend remain green |

## Done criteria

- [ ] Plans 001 and 003 are `DONE`.
- [ ] `/advisor/{runId}/compare?offers=...` loads one immutable persisted run.
- [ ] Search normalization preserves first-seen order, removes duplicates, and
      limits selections to three.
- [ ] Fewer than two valid same-run offers renders guidance without fallback.
- [ ] Two or three offers render aligned identity, offer, score, trade-off,
      evidence, freshness, provenance, and missing-data information.
- [ ] Advisor results allow selecting 2–3 offers and produce a shareable URL.
- [ ] No backend endpoint, migration, scoring, auth, or persistence change was
      added.
- [ ] Frontend tests, typecheck, and build pass.
- [ ] Backend lint and tests pass unchanged.
- [ ] Real browser reload restores the same comparison from its URL.
- [ ] Narrow viewport remains usable.
- [ ] `git diff --check` passes and scope contains only allowed paths.
- [ ] `plans/README.md` status row for 006 is updated.

## STOP conditions

Stop and report back if:

- Plan 001 or Plan 003 is not `DONE`.
- The Plan 001 route, response, or `AdvisorResults` shape differs materially
  from the expected post-dependency state.
- A compared item cannot be identified uniquely by `offer.id`.
- Implementing comparison appears to require recomputing scores or joining live
  catalog rows.
- The design starts comparing items from different runs.
- A backend change, database migration, authentication, local storage, or new
  dependency appears necessary.
- The generated TanStack route does not resolve to
  `/advisor/$runId/compare`.
- Existing result explanation or provenance would need to be removed to fit the
  comparison.
- A real full-stack browser check cannot be completed.
- Any verification fails twice after a reasonable correction.

## Maintenance notes

- Comparison semantics are tied to an immutable run. If run retrieval ever
  starts joining live listings instead of stored snapshots, revisit this
  feature before shipping.
- If price history is added later, show "price at recommendation time" and
  current price separately; never silently replace the stored decision.
- If authentication arrives, ownership/access control belongs at run retrieval,
  not inside the comparison matrix.
- A later checklist/report feature should reuse the same run and offer IDs. It
  must not introduce a second shortlist model unless user research proves the
  URL-state model insufficient.
