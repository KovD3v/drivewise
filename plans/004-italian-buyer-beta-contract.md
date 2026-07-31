# Plan 004: Define a fast, measurable Italian-buyer beta contract

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan in
> `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 70bfe86..HEAD -- README.md docs/product-beta.md`
>
> **IMPORTANT — this repo has a dirty working tree.** This plan was written
> against the working tree at commit `70bfe86`, which has extensive uncommitted
> changes. A diff against that SHA is not enough to detect drift. Confirm the
> "Current state" excerpts against disk before editing. Treat a mismatch as a
> STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `70bfe86`, 2026-07-31

## Why this matters

Drivewise has a broad technical surface and a broader long-term product vision,
but it does not yet define one initial buyer, one promise, or a measurable beta
outcome. Without that contract, a larger catalog can turn into an open-ended
data project and every new feature can look equally urgent.

This is intentionally a fast documentation plan. It defines the first product
wedge and a small manual validation protocol. It does not add analytics,
authentication, beta infrastructure, or runtime behavior.

## Current state

### Files in play

- `README.md` — currently describes the stack, setup, endpoints, and
  implementation scope. It has no product-validation link.
- `apps/web/src/views/Home.tsx` — current home page; useful evidence for the
  product surface, but **out of scope** for this plan.
- `apps/web/src/views/Advisor.tsx` — current buyer input and recommendation
  experience; **out of scope** for this plan.
- `docs/product-beta.md` — does not exist; this plan creates it.

### Current positioning is too broad to evaluate

`README.md:1-12`:

```markdown
# Drivewise

Drivewise is an MVP for a vehicle purchase assistant.

## Stack

- Frontend: TanStack Start
- Backend: FastAPI / Python
- Database: Neon PostgreSQL
```

The implemented Advisor asks for budget, one of five primary uses, new/used
condition, annual kilometres, fuel/body preferences, maximum used mileage, and
priorities. Its current Italian UI promise in
`apps/web/src/views/Advisor.tsx:183-188` is:

```tsx
<p className="eyebrow">Advisor deterministico</p>
<h1>Trova l'auto adatta</h1>
<p className="summary">
  Confronta offerte italiane nuove e usate. Ogni risultato mostra il
  motivo del punteggio, i compromessi e la provenienza dei dati.
</p>
```

The beta contract must preserve that evidence-first scope. It must not claim
that Drivewise predicts reliability, negotiates a purchase, guarantees an
offer, or replaces professional mechanical/legal advice.

### Product vocabulary to use

Use these terms consistently:

- **Vehicle family**: the model name buyers recognize across years/versions.
- **Exact variant**: trim, engine/powertrain, fuel type, and body style actually
  evaluated.
- **Market offer**: one new, used, or certified listing tied to the exact
  variant.
- **Reviewed source**: a source whose scope and ranking permission were
  explicitly assessed.
- **Evidence-backed shortlist**: recommendations that expose rationale,
  trade-offs, provenance, gaps, and uncertainty.

Do not replace these with generic AI-product language such as "smart matches",
"AI picks", or "personalized intelligence".

### Repo conventions to match

- Documentation is plain Markdown with short sections and fenced command
  examples. Match `docs/catalog-import.md`.
- README links use relative repo paths.
- No real user names, contact details, recordings, source credentials, private
  URLs, or raw interview transcripts may be committed.
- `AGENTS.md` requires a simple, locally runnable MVP and forbids secret
  material.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Confirm files | `test -f README.md && test ! -e docs/product-beta.md` | exit 0 before editing |
| Required sections | `rg -n "^## (Initial wedge|Product promise|Explicit non-goals|Beta prerequisites|Validation protocol|Pass and fail gates|Evidence handling)$" docs/product-beta.md` | exactly 7 matching headings |
| README link | `rg -n "docs/product-beta\\.md" README.md` | one match |
| Scope guard | `git diff --name-only -- README.md docs/product-beta.md` | only those two paths |
| Diff hygiene | `git diff --check -- README.md docs/product-beta.md` | exit 0, no output |

This plan changes documentation only. Do not run backend/frontend builds or
tests unless another concurrent change requires them.

## Scope

**In scope** (the only files you may modify or create):

- `docs/product-beta.md` (create)
- `README.md` (one relative link and one short sentence only)
- `plans/README.md` (status row only)

**Out of scope** (do not touch):

- Any code under `apps/`
- `Product.tldraw`
- Catalog fixtures or private source data
- Analytics, cookies, telemetry, authentication, or user accounts
- A public launch plan, pricing model, dealer workflow, or lead generation
- Recruiting participants or collecting actual beta data

## Git workflow

- Branch: `advisor/004-italian-buyer-beta-contract`
- One documentation commit using Conventional Commits, for example:
  `docs: define Drivewise beta contract`
- Do not push, open a PR, or merge unless the operator explicitly asks.

## Steps

### Step 1: Create the concise beta contract

Create `docs/product-beta.md` with exactly these top-level sections and
decisions.

#### `## Initial wedge`

State the initial user and job:

> An Italian private buyer who is actively choosing between reviewed new,
> used, or certified vehicle offers and needs to turn a budget plus real usage
> constraints into a defensible shortlist.

The document must make clear that this is the first validation wedge, not a
permanent exclusion of other future vehicle goals.

#### `## Product promise`

Use this single-sentence promise verbatim:

> Drivewise turns budget, usage, and preferences into an evidence-backed
> shortlist of exact vehicle variants and active offers, with visible
> trade-offs, provenance, assumptions, and uncertainty.

Then name the three user outcomes:

1. Identify 2–3 plausible offers.
2. Explain why the leading option fits and what its main compromise is.
3. Choose a concrete next action: inspect the offer, compare alternatives, or
   follow a purchase checklist.

#### `## Explicit non-goals`

List these non-goals:

- No purchase, financing, insurance, tax, legal, or mechanical guarantee.
- No dealer lead marketplace or paid placement.
- No ownership monitoring, upgrades/customization, maintenance planning, or
  resale workflow in this beta.
- No unreviewed source may affect ranking.
- No claim that synthetic fixtures prove market usefulness.
- No public launch until the prerequisites below are satisfied.

#### `## Beta prerequisites`

Define machine-checkable prerequisites:

- Plan 003 is `DONE`: the synthetic coverage tests and read-only
  `catalog_status.py` exist and pass.
- Plan 005 has an operator-approved source decision and a completed disposable
  database pilot report.
- Plan 001 is `DONE`: a user can reopen a recommendation run by URL.
- The selected beta dataset produces at least two eligible offers for each
  scenario used in a session.
- A reviewer has checked exact variant pairing, source permission, freshness,
  and metric provenance for every offer used in the beta scenarios.

The document must explicitly say that sessions before all prerequisites are
internal rehearsals, not evidence of public-beta readiness.

#### `## Validation protocol`

Keep the protocol intentionally small:

- Recruit 5 target users; do not store names or contact details in the repo.
- Give each participant one scenario that matches a genuine near-term purchase
  need.
- Ask them to create a shortlist, explain the first result, identify one
  uncertainty, and choose a next action.
- The observer may clarify the task but must not explain the UI or the scoring.
- Record only anonymized outcomes using participant IDs `P01`–`P05`.

Include a Markdown table template with these columns:

```text
Participant | Scenario | Non-empty shortlist | Chosen offer | Correct reason
identified | Uncertainty identified | Next action chosen | Needed help |
Trust-critical failure | Notes
```

#### `## Pass and fail gates`

Define these thresholds:

- At least 4/5 participants reach a non-empty shortlist without observer help.
- At least 4/5 correctly identify one evidence-backed reason for the leading
  result.
- At least 4/5 identify one trade-off, gap, assumption, or uncertainty.
- At least 4/5 choose a concrete next action.
- At least 3/5 say the result reduced manual comparison work enough that they
  would use Drivewise during a real purchase.
- **Zero trust-critical failures.** Define these as: wrong offer↔variant
  pairing, an unpermitted source affecting rank, unsupported provenance,
  materially stale offer presented as current, or hidden missing data that
  changes the decision.

State the decision rule:

- All gates pass → proceed to a larger private beta.
- Any trust-critical failure → stop beta expansion and fix/reverify it.
- Other misses → revise the smallest responsible part of the journey, then
  rerun only the failed task with new participants.

#### `## Evidence handling`

State:

- Commit only aggregate, anonymized outcomes.
- Keep recruitment details, recordings, and raw notes outside the repository.
- Never put secrets, private source snapshots, emails, phone numbers, names, or
  vehicle registration/VIN data in Git.
- A future analytics plan requires separate approval; this plan introduces no
  tracking.

**Verify**:

```bash
rg -n "^## (Initial wedge|Product promise|Explicit non-goals|Beta prerequisites|Validation protocol|Pass and fail gates|Evidence handling)$" docs/product-beta.md
```

Expected: exactly seven lines, one for each required section.

### Step 2: Link the contract from the README

In `README.md`, immediately after the opening sentence, add one short paragraph:

```markdown
The initial product wedge and private-beta gates are defined in
[`docs/product-beta.md`](docs/product-beta.md).
```

Do not rewrite the README, alter setup commands, or broaden the Scope section.

**Verify**:

```bash
rg -n "docs/product-beta\\.md" README.md
```

Expected: exactly one match.

### Step 3: Run the documentation gates

Run:

```bash
git diff --check -- README.md docs/product-beta.md
git diff --name-only -- README.md docs/product-beta.md
```

Expected:

- `git diff --check` exits 0 with no output.
- The name-only output contains exactly `README.md` and
  `docs/product-beta.md`.

Do a final secret/PII guard:

```bash
rg -n -i "api[_ -]?key|password|token|cookie|email|phone|vin|targa" docs/product-beta.md
```

Expected: only policy/non-goal prose, never a value or participant detail.

## Test plan

This is documentation-only. Verification consists of:

- Required-heading check.
- README relative-link check.
- Scope check.
- `git diff --check`.
- Manual confirmation that no PII, secret, private URL, or raw research record
  was added.

Do not add runtime tests.

## Done criteria

- [ ] `docs/product-beta.md` exists with all seven required sections.
- [ ] The initial user, promise, non-goals, prerequisites, five-person
      protocol, pass/fail thresholds, and evidence policy are explicit.
- [ ] Trust-critical failure is defined and has a zero-tolerance gate.
- [ ] README links to the contract exactly once.
- [ ] `git diff --check -- README.md docs/product-beta.md` exits 0.
- [ ] No code, dependency, fixture, analytics, or user-data change exists.
- [ ] `plans/README.md` status row for 004 is updated.

## STOP conditions

Stop and report back if:

- `docs/product-beta.md` already exists with materially different product
  decisions.
- The operator wants a different initial user than an Italian private buyer
  choosing reviewed new/used/certified offers.
- The work starts requiring analytics, authentication, participant
  recruitment, or runtime changes.
- A requested beta record would contain personal data, private source data, or
  secrets.
- Any verification fails twice after a reasonable correction.

## Maintenance notes

- Review the thresholds after the first five sessions; do not silently loosen
  a failed trust gate.
- If the product expands to ownership, monitoring, upgrades, or resale, create
  a separate validation contract for that intent rather than broadening this
  one.
- Plan 003 supplies corpus visibility, Plan 005 supplies the real-source pilot,
  and Plan 001 supplies result continuity. This contract is the acceptance
  layer above those capabilities.
