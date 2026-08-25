# Advisor v3 unified decision engine design

**Status:** Approved
**Date:** 2026-08-24
**Target branch:** `feat/advisor-v3-unified-engine`
**Base:** `origin/main` at `7b683b6`

## Purpose

Drivewise currently has two deterministic ranking implementations:

- Advisor v2 is integrated with FastAPI, PostgreSQL, exact vehicle/spec/offer
  identity, source permissions, freshness checks, provenance, and persisted
  recommendation runs.
- Decision Engine v1 has the broader product model: six structural pillars,
  ordered preferences, TCO, garage fit, powertrain fit, reliability and safety,
  known-issue and recall penalties, Vehicle DNA, confidence, and richer
  explanations. It runs from mock JSON and is not integrated with the app.

Advisor v3 combines them into one runtime. It preserves Advisor's trust and
operational boundaries while implementing every Decision Engine v1 capability.
Specialist data modules may be added later without changing the scoring
contract.

## Goals

- Make `advisor-v3.0` the only production ranking implementation.
- Keep `POST /advisor/recommendations` backward compatible with v2 requests.
- Preserve exact vehicle, spec, and offer ranking.
- Preserve source permission, review, freshness, and provenance gates.
- Implement all Decision Engine v1 scoring capabilities.
- Add a stateful Guided Decision contract that can collect the richer profile.
- Use estimated TCO immediately and make its assumptions explicit.
- Return `insufficient_data` instead of inventing neutral values.
- Persist enough breakdown data to reproduce and audit every score.
- Document the specialist modules required to replace estimates with sourced
  calculations.

## Non-goals

- No frontend redesign.
- No LLM-owned scoring, constraint selection, or question priority.
- No live source ingestion, Firecrawl integration, or automatic publication of
  unreviewed data.
- No claim that heuristic scores or the synthetic calibration benchmark are
  real-world automotive validation.
- No compatibility promise for the standalone `decision_engine` Python API.
- No new provider framework, abstract base class, or dependency injection
  container. Versioned functions and typed values are sufficient.

## Definition of complete

This PR is capability-complete when Advisor v3 can evaluate every Decision
Engine v1 factor from typed module inputs and expose the result through the
integrated API. Capability completion does not mean every production candidate
already has every specialist input.

- TCO has a working estimated implementation in this PR.
- Vehicle Knowledge Profile supplies available dimensions, maintenance, safety,
  feature, powertrain, efficiency, and performance facts.
- Reliability, known issues, recalls, Vehicle DNA, valuation, and folded-mirror
  dimensions have typed contracts and fully tested scoring behavior.
- Until their specialist producers exist, those contracts return
  `insufficient_data` for real candidates rather than mock values.
- A later producer can activate a factor without changing the Advisor request,
  scoring API, persistence shape, or frontend response contract.

## Chosen approach

Advisor v2 remains the operational spine. Decision Engine v1 capabilities move
into focused modules under `apps/api/app/services/advisor/`. The standalone
runtime is retired after its behavior is covered by Advisor v3 tests. Historical
calibration reports remain under documentation and the mock dataset remains a
clearly labelled development fixture.

The rejected approaches are:

1. Running Advisor v2 eligibility followed by a separate Decision Engine v1
   ranking. This creates two score authorities and two explanation models.
2. Exposing v2 and v3 concurrently. This doubles maintenance and makes persisted
   runs harder to compare.
3. Copying the v1 JSON data into production ranking. Its values are useful for
   calibration, not sufficient evidence for purchase guidance.

## Prerequisite work included in the PR

### Vehicle Knowledge Profile

The existing `feat/vehicle-knowledge-profile` work is integrated before Advisor
v3 scoring. It provides migration `0005_vehicle_knowledge_profile.sql`, curated
profile validation, ingestion, and source-aware storage for:

- dimensions and weights;
- powertrain, transmission, efficiency, and performance;
- maintenance schedules;
- safety ratings;
- ADAS, safety, comfort, and technology features.

The integration must retain its current guarantees:

- scalar absence is `null`;
- collection absence is `[]`;
- omitted collections preserve existing rows;
- explicit empty collections remove existing rows;
- child records carry direct provenance;
- malformed or non-HTTPS provenance is rejected.

### Guided Decision

The existing local Guided Decision work is ported into the isolated branch and
extended rather than rewritten. Migration `0006_guided_decisions.sql` remains
additive, and migration `0007_https_primary_provenance.sql` follows it for
forward-only primary URL validation. The flow persists the current profile and
append-only turn snapshots,
uses optimistic concurrency through `expectedProfileVersion`, and delegates
ranking to Advisor v3.

The interpreter remains a conservative Italian baseline. A future LLM adapter
may produce typed profile facts, but it cannot own scoring, constraints, or
question ordering.

## Runtime architecture

```text
Guided Decision or direct Advisor request
                    |
                    v
          Decision Profile v3
                    |
                    v
       Advisor repository eligibility
     exact vehicle + spec + fresh offer
                    |
                    v
        Decision input assembly
                    |
       +------------+-------------+
       |            |             |
       v            v             v
     TCO       vehicle facts   specialist inputs
   estimate      and safety      when available
       |            |             |
       +------------+-------------+
                    |
                    v
        constraints and modules
                    |
                    v
     Structural Fit + Preference Fit
                    |
                    v
 confidence + explanation + persistence
```

There is one ranking call and one final score. Modules return inputs or
assessments to the scoring function. They do not rank candidates independently.

## Request contract

`AdvisorRecommendationRequest` retains all v2 fields. The following additions
are optional so an existing request remains valid:

- `usage`: ordered unique list of use cases. When absent, it becomes
  `[primary_use]`.
- `children_count`: non-negative integer.
- `passengers_usual`: positive integer.
- `garage`: useful internal length, width, height, door width, and door height
  in millimetres.
- `automatic_required`: boolean.
- `constraint_modes`: typed modes for budget, body style, fuel type,
  transmission, and garage. Each mode is `hard` or `soft`.

Existing fields keep their meaning:

- `condition` and `max_mileage` remain hard constraints.
- `preferred_body_style` and `preferred_fuel_type` remain soft unless their
  corresponding mode is explicitly `hard`.
- the legacy budget behavior retains the 10 percent tolerance. An explicit
  hard budget uses the exact maximum.
- absent new fields preserve v2 behavior.

The priority vocabulary expands to cover the v1 model:

- `price`
- `budget`
- `running_cost`
- `space`
- `family`
- `reliability`
- `safety`
- `comfort`
- `performance`
- `technology`
- `efficiency_range`
- `powertrain_fit`

The first three priorities are ordered and weighted 50, 30, and 20 percent.
Additional priorities remain accepted for request compatibility but do not
affect Preference Fit. The response assumptions disclose this rule.

## Module result contract

All replaceable calculations return the same small metadata envelope alongside
their module-specific values:

```json
{
  "status": "available | estimated | insufficient_data",
  "version": "module-name-v1",
  "assumptions": [],
  "evidence": [],
  "missing_data": []
}
```

This is a shared Pydantic value model, not a provider interface. Each module is
a normal deterministic function. Replacing an estimator changes the function's
input assembly, not the ranking contract.

Rules:

- `available` requires accepted evidence for the exact spec or offer.
- `estimated` requires named assumptions and an assumption version.
- `insufficient_data` contributes no neutral score.
- every score records the producing module version.
- evidence used for a trust-sensitive value must retain source URL and observed
  date when those fields exist.

## Constraint evaluation

Constraints run before scoring and return one result per candidate:

- `eligible`
- `excluded`
- `insufficient_data`

A hard constraint excludes only when the available value proves the candidate
does not match. If the value needed to evaluate a hard constraint is missing,
the candidate is `insufficient_data`; it is never treated as matching.

Soft constraints produce fit scores and trade-offs. Missing soft-constraint
data removes that factor from the calculation and lowers confidence.

### Family and passengers

- `passengers_usual` defines the minimum required seat count when present.
- insufficient seat capacity is a hard exclusion.
- missing seat count is `insufficient_data`.
- `children_count` affects the family practicality target, not seat count by
  implication.
- the `family-fit-v1` cargo target is versioned and documented in the response.
  It starts at 250 litres and adds 75 litres per child, capped at 550 litres.
- cargo remains a soft score unless the future request contract adds an
  explicit hard cargo constraint.

### Garage

Garage evaluation uses:

- useful internal length against overall vehicle length;
- useful internal width against body width;
- useful internal height against vehicle height;
- door width against width with mirrors folded;
- door height against vehicle height.

Any missing required measurement returns `insufficient_data`. No missing value
is replaced with zero. A hard garage constraint excludes an incompatible
candidate and blocks a definitive fit claim when data is insufficient. A soft
garage constraint affects Practicality when complete and otherwise lowers
confidence.

## Structural Fit

Structural Fit contains the six Decision Engine v1 pillars:

1. Economics
2. Practicality
3. Reliability and Safety
4. Driving
5. Technology
6. Powertrain Fit

The starting pillar weights are retained from v1:

| Pillar | Weight |
| --- | ---: |
| Economics | 26.6667% |
| Practicality | 17.7778% |
| Reliability and Safety | 22.2222% |
| Driving | 11.1111% |
| Technology | 11.1111% |
| Powertrain Fit | 11.1111% |

Priorities do not boost these weights. Decision Engine v1 applied priorities to
both structural weights and Preference Fit, which counted the same preference
twice. Advisor v3 keeps structural weights stable and applies user ordering only
through Preference Fit.

When a complete pillar is unavailable, remaining pillar weights are
renormalized. The missing pillar is listed in `missing_factors`, and confidence
falls. At least Economics and Practicality must be calculable for a candidate to
receive a final score.

### Economics

Economics combines:

- exact offer price fit;
- estimated or sourced annual TCO;
- running-cost fit.

`tco-v1` is implemented now. Its annual breakdown includes:

- energy or fuel;
- insurance estimate;
- vehicle tax estimate;
- maintenance estimate;
- tyre estimate;
- depreciation estimate.

The module reuses current MIMIT and ARERA energy assumptions. Other components
use deterministic versioned estimates until a sourced TCO provider replaces
them. The response includes every amount and assumption. Financing is excluded
because it was not part of Decision Engine v1 and depends on an individual
credit product.

### Practicality

Practicality combines:

- body-style fit;
- all declared usage contexts;
- passenger and family fit;
- seats and cargo;
- garage fit when requested.

### Reliability and Safety

Safety is calculated from Vehicle Knowledge Profile ratings and safety features
when present. Reliability consumes a versioned specialist assessment. Until the
Reliability Assessment module exists, reliability is
`insufficient_data`; safety can still contribute and the subfactor weights are
renormalized.

The future reliability assessment must provide:

- exact generation and spec applicability;
- source observations;
- sample and time window when statistical;
- normalized score;
- confidence and missing data.

### Driving

Driving uses available performance, comfort, travel, and vehicle-control facts.
It does not infer a subjective score from horsepower alone. A future Vehicle DNA
assessment may supply calibrated comfort, sport, and travel values. Until then,
supported objective facts contribute and unavailable subjective factors are
listed.

### Technology

Technology uses curated technology features with provenance. Feature count
alone is not treated as universal quality. `vehicle-dna-v1` may later provide a
calibrated technology score without changing the pillar contract.

### Powertrain Fit

`powertrain-fit-v1` extends the current thresholds to:

- petrol;
- diesel;
- mild hybrid;
- full hybrid;
- plug-in hybrid;
- electric;
- LPG.

No recognized powertrain is excluded solely because an earlier Advisor version
did not model it. Missing consumption, range, charging, or usage inputs yield
`insufficient_data` for the affected subfactor. Safety and source eligibility
gates still apply.

## Preference Fit

Preference Fit maps each of the first three ordered priorities to the most
direct available metric or pillar. It uses weights 50, 30, and 20 percent.

If one preferred factor is unavailable, available preference weights are
renormalized and the missing priority lowers confidence. If no preference can be
calculated, Preference Fit is `insufficient_data`; the response does not invent
a score of 70.

## Penalties

Known issues and recalls remain separate from positive fit scores.

### Known issues

`known-issues-v1` consumes issue records with:

- generation, spec, engine, transmission, and production-year applicability;
- severity and frequency;
- evidence and observed date;
- repair-cost range when available;
- applicability confidence.

An issue with ambiguous applicability does not silently penalize every variant.
It is exposed as a warning and lowers confidence. Confirmed applicable issues
produce capped, versioned penalties.

### Recalls

`recalls-v1` consumes official recall assessments with applicability and status.
Open applicable recalls produce a penalty and warning. Resolved recalls remain
visible but do not receive the same penalty. Unknown applicability is reported,
not guessed.

Until the specialist registries exist, both modules return
`insufficient_data`. Their scoring and explanation behavior are still covered
by contract tests using explicit module inputs.

## Final score

```text
Decision Score = 65% Structural Fit + 35% Preference Fit
```

If Preference Fit is unavailable, the candidate may still receive a provisional
Structural Fit result, but `decision_status` is `insufficient_data` and
`decision_score` is `null`. The legacy numeric `score` contains the provisional
Structural Fit so existing clients can still render an ordered result, while
the new status prevents it from being presented as a complete decision score.
Penalties apply to Structural Fit before the 65/35 composition and are capped so
they cannot make a score negative.

Ranking remains deterministic. Complete candidates sort before provisional
candidates. Within each status, the stable tie-break order is:

1. decision score, or provisional structural score, descending;
2. decision confidence descending;
3. offer price ascending;
4. mileage ascending with missing last;
5. listing reference;
6. listing ID.

Family deduplication remains per new or used group after ranking.

## Decision Confidence

Decision Confidence is a heuristic signal, not a probability of purchase
success. `decision-confidence-v1` combines:

- profile completeness: 45 percent;
- data and evidence completeness: 35 percent;
- ranking stability: 20 percent.

Profile completeness distinguishes user-provided values from defaults. Evidence
completeness measures available required factors, provenance, and freshness.
Ranking stability uses the score gap within the relevant condition group.

The response exposes all three components, module version, missing data, and a
plain-language warning that the value is not a calibrated probability.

## Response compatibility

`POST /advisor/recommendations` and its current fields remain. Each item adds:

- `decision_status`: `complete` or `insufficient_data`;
- `decision_score`: the complete 65/35 score or `null`;
- `decision_confidence`;
- `structural_fit`;
- `preference_fit`;
- `pillar_scores`;
- `penalties`;
- `strengths`;
- `missing_factors`;
- `module_versions`;
- `score_composition`.

Existing `component_scores`, `positive_factors`, `tradeoffs`, `evidence`, and
`provenance` remain populated. For complete results, `score` equals
`decision_score`. For insufficient results, `score` is the explicitly
provisional Structural Fit retained for existing consumers. The assumptions and
warnings disclose that compatibility behavior.

The top-level response reports `advisor-v3.0`, assumptions, exclusion counts,
and condition groups. It adds counts for `insufficient_data` reasons so an empty
group is distinguishable from no inventory.

## Persistence

Existing `recommendation_items.score_breakdown` JSONB stores the complete v3
breakdown, including confidence, pillars, penalties, missing factors, module
versions, assumptions, and evidence. No new scoring migration is required.

`recommendation_runs.request_payload` records:

- normalized v3 profile;
- scoring version;
- evaluation timestamp;
- defaulted fields;
- constraint modes;
- active module versions.

Guided Decision persistence remains in migration `0006`. Vehicle Knowledge
Profile remains migration `0005`; primary provenance HTTPS constraints are in
forward migration `0007`.

## Specialist prerequisite modules

The following modules are documented contracts in this PR and can be delivered
independently later:

| Module | Output consumed by v3 | Required source properties |
| --- | --- | --- |
| Reliability Assessment | score, confidence, evidence, applicability | exact spec/generation, dated observations |
| Known Issues Registry | applicable issues and repair ranges | engine/transmission/year applicability |
| Official Recall Resolver | recall status and applicability | official source, campaign identity, dates |
| Vehicle DNA Calibration | comfort, family, sport, travel, technology | documented rubric and calibration set |
| TCO Data Provider | sourced cost breakdown | market, date, usage, currency, assumptions |
| Valuation Provider | current and residual values | exact variant, condition, mileage, market date |
| Garage Dimension Provider | body and folded-mirror dimensions | exact spec, measurement semantics, source |

The current TCO estimator is the only temporary specialist implementation that
contributes estimated values immediately.

## Standalone Decision Engine retirement

The implementation ports v1 behavior into Advisor v3 tests before removing the
standalone runtime modules. The following artifacts are retained:

- calibration reports as historical documentation;
- the 12 synthetic profiles as a non-production calibration fixture where they
  can be mapped without bypassing Advisor eligibility;
- Dataset v0.2 with its existing mock disclaimer.

The standalone package must not remain callable as a second ranking authority.

## Error handling

- Invalid request values return FastAPI validation errors.
- Unsupported but recognized powertrains are assessed or marked
  `insufficient_data`, not rejected by a legacy allowlist.
- Source, review, identity, and freshness failures remain exclusions.
- Hard constraints with missing evidence return explicit insufficient-data
  reasons.
- Module exceptions fail the affected module closed and record a warning. They
  do not silently substitute a neutral score.
- Database persistence remains transactional. A failed item write does not
  leave a completed run.

## Testing strategy

Implementation follows test-driven development. Each behavior is first added as
a failing test.

### Unit tests

- exact 65/35 composition;
- ordered 50/30/20 preferences;
- no double counting of priorities;
- pillar and subfactor renormalization;
- TCO breakdown and estimate labels;
- every supported powertrain path;
- family and passenger rules;
- hard and soft constraints;
- garage `insufficient_data`, compatible, tight, and incompatible states;
- known-issue and recall applicability;
- confidence components and bounds;
- stable ordering under candidate permutation;
- no neutral fallback for missing data.

### Contract and API tests

- existing v2 requests remain accepted;
- new fields serialize without removing existing fields;
- exact offer identity and provenance remain present;
- insufficient-data reasons are distinguishable from exclusions;
- run and item breakdowns persist and round-trip;
- Guided Decision produces the v3 request and preserves optimistic concurrency.

### Data and migration tests

- migrations apply from an empty database through `0007`;
- Vehicle Knowledge Profile omitted-versus-empty behavior remains correct;
- malformed provenance and invalid profile values fail validation;
- Advisor repository returns the exact facts needed by modules.

### Regression and full checks

- all API tests;
- Ruff;
- Decision Engine v1 tests until retirement mapping is complete;
- frontend tests;
- frontend typecheck;
- production frontend build;
- disposable PostgreSQL and browser smoke when the implementation is complete.

## Delivery and review boundaries

The PR targets `main` and contains no frontend redesign. It must explain:

- the score semantic change from Advisor v2 to v3;
- backward-compatible request and response behavior;
- which inputs are sourced, estimated, or unavailable;
- which specialist modules remain prerequisites;
- why the synthetic benchmark is not real-world validation;
- how to replace the TCO estimator without changing scoring consumers.

The existing dirty `main` checkout is not modified. All implementation and PR
feedback remain in the isolated worktree until the PR is merged.
