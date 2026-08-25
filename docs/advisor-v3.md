# Advisor v3

## Runtime boundary

Advisor v3 is the only ranking runtime. `POST /advisor/recommendations` and
Guided Decision previews call [`scoring.py`](../apps/api/app/services/advisor/scoring.py).
The scorer reads reviewed catalog offers and exact vehicle variants, applies
constraints and module assessments, and returns a deterministic ranking.

The old `decision_engine/` Python package, demo, tests, and requirements file
are retired. The reports in `docs/snapshots/` and calibration JSON in
`dataset/mvp-v0.2/calibration/` are historical, non-runtime material. The
dataset keeps its mock-data disclaimer.

No future specialist module is treated as present merely because its adapter
exists. The active runtime and its current inputs are listed below.

| Area | Runs now | Current input or fallback | Replacement boundary |
| --- | --- | --- | --- |
| Ranking | Yes, `advisor-v3.0` | Reviewed Italian offers, exact specs, profile, provenance | Keep the scoring and response contract stable |
| Safety | Yes, `safety-v1` | Curated Knowledge Profile ratings. ADAS/features remain in `decision_context` but are not scored | Replace the rating input, not pillar composition |
| Reliability | Adapter only, `reliability-v1` | `insufficient_data` without an explicit assessment | Produce a versioned assessment for the exact generation/spec |
| Known issues | Adapter only, `known-issues-v1` | `insufficient_data` without issue records | Produce applicability-first issue records |
| Official recalls | Adapter only, `recalls-v1` | `insufficient_data` without official records | Produce campaign identity, status, and applicability |
| Vehicle DNA | Adapter only, `vehicle-dna-v1` | `insufficient_data` without calibrated factor values | Produce calibrated factor values and evidence |
| TCO | Yes, `tco-v1` estimated module | Versioned energy rates and deterministic estimates | Replace the estimate provider or input without changing the scoring contract |
| Valuation | Not implemented | No valuation module is called by v3 | Produce exact-variant market and residual values |
| Garage dimensions | Yes when requested, `garage-fit-v1` | Catalog dimensions, including folded-mirror width | Replace catalog measurements with sourced exact-spec measurements |

## Score and pillars

The complete score is:

```text
Decision Score = 65% Structural Fit + 35% Preference Fit
```

Structural Fit has six pillars. The weights are stable and do not change when
the user reorders priorities.

| Pillar | Weight |
| --- | ---: |
| Economics | 26.6667% |
| Practicality | 17.7778% |
| Reliability and Safety | 22.2222% |
| Driving | 11.1111% |
| Technology | 11.1111% |
| Powertrain Fit | 11.1111% |

Available pillar weights are renormalized when a pillar is unavailable. At
least Economics and Practicality must be calculable for a structural result.
For available pillar set `A`, the scorer uses:

```text
normalized_pillar_weight(p) = pillar_weight(p) / sum(pillar_weight(a) for a in A)
Structural Fit = sum(pillar_score(p) × normalized_pillar_weight(p) for p in A)
```

The same rule applies inside each pillar. If `C` is the set of available
subfactors, the subfactor score is:

```text
pillar_score = sum(subfactor_score(c) × subfactor_weight(c) for c in C)
               / sum(subfactor_weight(c) for c in C)
```

The implementation is [`_compose_pillars`](../apps/api/app/services/advisor/scoring.py#L825).
It records missing subfactors instead of replacing them with zero. The
implementation is [`_structural_fit`](../apps/api/app/services/advisor/scoring.py#L850).
It subtracts the known-issues penalty first, then the recall penalty, then
clamps the result to `[0, 100]`:

```text
unclamped_structural = weighted_pillars - known_issues_penalty - recall_penalty
Structural Fit = min(100, max(0, unclamped_structural))
```

Preference Fit maps the first three ordered priorities to direct metrics with
weights 50%, 30%, and 20%. For available priority values `P`, the weights are
renormalized in the same way:

```text
Preference Fit = sum(metric_value(i) × preference_weight(i) for i in P)
                 / sum(preference_weight(i) for i in P)
```

Missing preference metrics lower confidence. If no mapped metric is available,
Preference Fit is `null` and the scorer never invents a neutral value. The
implementation is [`_preference_fit`](../apps/api/app/services/advisor/scoring.py#L865).

The complete score is calculated only when Preference Fit exists:

```text
Decision Score = round(0.65 × Structural Fit + 0.35 × Preference Fit, 1)
```

The implementation is [`_score_candidate`](../apps/api/app/services/advisor/scoring.py#L495). If the score cannot be completed, v3 sets
`decision_status=insufficient_data` and `decision_score=null`. The legacy
`score` field contains `round(Structural Fit, 1)` for ordering and old clients.
It is not presented as a complete Decision Score.

The pillar component contracts are:

- Economics: price fit 45%, TCO 40%, running cost 15%.
- Practicality: category 22%, usage 33%, family 25%, garage 20%.
- Reliability and Safety: reliability 58%, safety 42%.
- Driving: comfort 48%, sport 22%, travel 30%.
- Technology: calibrated technology input when available.
- Powertrain Fit: the versioned powertrain assessment.

Decision Confidence uses the bounded weighted sum in
[`confidence.py`](../apps/api/app/services/advisor/confidence.py):

```text
Decision Confidence = clamp(
    0.45 × profile_completeness
  + 0.35 × evidence_completeness
  + 0.20 × ranking_stability,
  0, 100
)
```

The result is rounded to one decimal place. The three inputs are percentages,
not probabilities. Ranking stability is the bounded score gap between the top
two candidates in a condition group.

## Status and compatibility

`advisor-v3.0` preserves the v2 request fields and the existing response
fields, including `score`, `component_scores`, `positive_factors`,
`tradeoffs`, `evidence`, and `provenance`. New fields include
`decision_status`, `decision_score`, `decision_confidence`, `structural_fit`,
`preference_fit`, `pillar_scores`, `penalties`, `missing_factors`,
`module_versions`, and `score_composition`.

Decision status is `complete` when both score parts are available and
`insufficient_data` otherwise. For the latter, `decision_score` is `null`.
The legacy numeric `score` contains the provisional Structural Fit so existing
clients can order and render an item, but the status prevents it being shown as
a complete Decision Score. A module status is `available`, `estimated`, or
`insufficient_data`. Constraint status is `eligible`, `excluded`, or
`insufficient_data`.

Hard constraints exclude a candidate. Soft constraints add a trade-off and
leave the candidate scoreable. Budget, body style, fuel type, transmission,
garage mode, passenger count, condition, and mileage use the request's
constraint modes. Missing required evidence produces `insufficient_data`, not
an exclusion or a zero value unless a hard constraint has enough evidence to
prove incompatibility.

Family fit uses `min(550, 250 + 75 * children_count)` litres as the cargo target.
Passenger requests require a known seat count. A missing cargo value makes
family fit insufficient. Garage fit checks useful length, body width, height,
door height, and door width against the vehicle width with mirrors folded.
Missing measurements are insufficient data. A hard incompatible garage
excludes the candidate; a soft incompatible garage is a trade-off.

`powertrain-fit-v1` assesses petrol, diesel, mild hybrid, full hybrid,
plug-in hybrid, electric, and LPG. It uses annual distance and city/highway
usage thresholds. The notable thresholds are 15,000 km for the city baseline,
25,000 km for high-distance petrol adjustment, 30,000 km for long-distance
adjustment, 22,000 km for the diesel highway adjustment, and 250 km WLTP as an
EV highway reference. PHEVs also require consumption, electric range, and a
charging context. Recognized powertrains are assessed or marked insufficient,
not rejected by the old allowlist.

## TCO assumptions

`estimate_tco()` runs now as `tco-v1`. It returns a version, assumptions,
component amounts, and an annual total. The estimate includes energy or fuel,
insurance, tax, maintenance, tyres, and depreciation when their inputs exist.
The energy formula is:

```text
consumption × rate × annual_km ÷ 100
```

The scorer turns the annual TCO amount into its Economics metric in
[`_tco_assessment`](../apps/api/app/services/advisor/scoring.py#L886). It uses
the request budget in euro:

```text
target_eur = max(3500, 0.22 × budget_max_eur)
ratio = annual_tco_eur / target_eur

TCO fit = 100                         when ratio <= 0.85
          95                          when 0.85 < ratio <= 1.00
          max(0, 95 - (ratio - 1)×42) when ratio > 1.00
```

The current fixed inputs are the versioned MIMIT and ARERA rates in
`apps/api/app/services/advisor/energy_prices.py`: petrol and hybrid
EUR 1.91662/L, diesel EUR 2.04276/L, LPG EUR 0.77695/L, and electricity EUR
0.29593/kWh under `it-energy-2026-07-16-v1`. Insurance is EUR 650 plus 0.8% of
offer price, capped at EUR 1,600. Tax is EUR 2.58/kW through 100 kW and EUR
3.87/kW above 100 kW. Maintenance and tyres use the named `maintenance-v1`
and body-class assumptions returned in the response. Depreciation is 9.333%
of offer price per year.

TCO works now from versioned estimates. Replacing it means swapping the
estimate provider or its input data. Consumers continue to read the same
`ModuleAssessment` value, details, assumptions, version, and missing-data
fields. Financing is not part of this contract.

## Metric fit equations

The v3 pillar inputs use these deterministic metric functions from
[`scoring.py`](../apps/api/app/services/advisor/scoring.py). Scores are on a
`0..100` scale. Prices and TCO amounts are euro, running cost is euro per
100 km, liquid consumption is litres per 100 km, electric consumption is kWh
per 100 km, range is km, seats are a count, and cargo is litres.

Price fit uses `ratio = offer_price_eur / budget_max_eur`:

```text
100                                      when ratio <= 0.75
100 - ((ratio - 0.75) / 0.25) × 30       when 0.75 < ratio <= 1.00
max(0, 70 - ((ratio - 1.00) / 0.10)×70)  when ratio > 1.00
```

Running-cost fit is a descending linear score between EUR 5 and EUR 15 per
100 km:

```text
100                         when cost_eur_100km <= 5
0                           when cost_eur_100km >= 15
(15 - cost_eur_100km)/10×100 otherwise
```

Use-case fit looks up the body score in the primary-use matrix, then applies
the fuel and body preferences:

```text
use_case_fit = 0.60 × body_use_matrix_score
             + 0.20 × fuel_preference_score
             + 0.20 × body_preference_score
```

Each preference score is `100` when absent or matching and `0` when the
request specifies a different value. Space fit uses four seats for city,
highway, and new-driver use, five seats for family and work, and the cargo
bands in the code. If `required_seats` is the target and `cargo_score` is the
ascending linear score in the selected band:

```text
seat_score = min(seats / required_seats × 100, 100)
space_fit = 0.40 × seat_score + 0.60 × cargo_score
```

Liquid efficiency uses a descending linear score from 4 to 8 L/100 km.
Electric efficiency uses the average of a descending 14 to 24 kWh/100 km score
and an ascending 150 to 500 km WLTP range score. Family fit uses
`min(100, cargo_litres / target_litres × 100)` where
`target_litres = min(550, 250 + 75 × children_count)`. Garage fit is `100` when
all five measured margins are non-negative and `0` when any margin is
negative. Missing measurements return `insufficient_data`.

## Specialist input contracts

The current adapters are narrow. They validate the values they consume, but
they do not enforce the full future-provider contract below. A producer that
supplies production data must add exact identity, applicability, version, and
evidence before its output is treated as sourced.

Current behavior is specific to each adapter:

- [`safety.py`](../apps/api/app/services/advisor/safety.py) reads only curated
  `decision_context.safety.ratings`. It validates percentage values in `0..100`
  and star values in `0..5`, then averages percentages or converts stars to a
  percentage. It does not validate source metadata, identity, or observation
  dates. ADAS and other features remain in context for a future producer and
  do not contribute to `safety-v1` today.
- [`reliability.py`](../apps/api/app/services/advisor/reliability.py) accepts
  an explicit numeric `decision_context.reliability_assessment.value`, clamps
  it to `0..100`, and uses the supplied version, details, evidence, and missing
  data when present. Version and evidence are optional in this adapter, and
  the default is `reliability-v1`.
- [`vehicle_dna.py`](../apps/api/app/services/advisor/vehicle_dna.py) accepts
  explicit numeric factor values in `decision_context.vehicle_dna`, clamps
  each to `0..100`, and accepts optional version, details, and evidence. The
  default version is `vehicle-dna-v1`; feature evidence alone does not create a
  factor score.
- Known-issue and recall adapters apply the applicability and status values
  supplied in context. They do not fetch registries or verify an external
  source record.

The following are future producer contracts and replacement boundaries:

| Module | Input contract | Identity and applicability keys | Evidence and status requirements |
| --- | --- | --- | --- |
| Safety Assessment | Curated ratings for the exact variant/spec | Exact variant/spec, assessment system, assessment year, market | Future producer supplies source, observed date, version, and applicability; current `safety-v1` validates rating ranges only and returns `insufficient_data` without ratings |
| Reliability Assessment | Normalized score, confidence, missing data, details | Generation, exact variant/spec, powertrain where relevant | Future producer supplies dated observations, sample and time window when statistical, source and version; current adapter accepts an explicit numeric value |
| Known Issues Registry | Issue severity/frequency, repair range, applicability | Generation, variant/spec, engine, transmission, production-year bounds | Evidence and observed date; ambiguous applicability is a warning, confirmed issues use capped `known-issues-v1` penalty |
| Official Recall Resolver | Campaign records, status, applicability | Exact vehicle/spec plus campaign identity and market | Official source, campaign date and observed date; `open`, `resolved`, or `unknown` status; unknown applicability is not guessed |
| Vehicle DNA Calibration | Comfort, family, sport, travel, and technology values | Exact generation/spec and calibration scope | Future producer supplies a versioned rubric, calibration set, feature evidence, and source; current adapter accepts explicit numeric factors with optional version/evidence |
| TCO Data Provider | Energy, insurance, tax, maintenance, tyres, depreciation amounts | Market, currency, annual usage, offer/spec, valuation date | Source, observed date, assumptions, and provider version |
| Valuation Provider | Current value and residual value | Exact variant, condition, mileage, market, valuation date | Source, observed date, sample/method, assumptions, and provider version |
| Garage Dimension Provider | Length, body width, height, folded-mirror width | Exact spec and measurement semantics | Source, observed date, units, and whether folded width is measured or inferred |

The replacement boundary is the module input, not the scorer. A future producer
writes the validated assessment into the corresponding `decision_context`
field, keeps the module version and evidence, and leaves the scoring formulas
unchanged. Until then, missing data remains `insufficient_data`.

## Audit and persistence

Each recommendation run stores the normalized request, scoring version,
evaluation time, defaulted fields, constraint modes, active module versions,
assumptions, exclusion counts, status, and completion time. Each item stores
the exact vehicle, listing, and spec identity, condition group, rank, score,
scoring version, and the full v3 breakdown in
`recommendation_items.score_breakdown`.

The breakdown includes confidence components, pillar and preference scores,
penalties, missing factors, module versions, assumptions, evidence, and
provenance. Guided Decision persistence keeps the current profile and every
turn snapshot with profile version, changed fields, response, and optimistic
concurrency data. These records make an output auditable without treating
conversation text as the only source of truth.

## Benchmark limits

The historical calibration used 12 synthetic scenarios and reported 100%
Top-2 acceptance and MRR 0.958. The reports are
`docs/snapshots/2026-08-24_STANDALONE_ENGINE_CALIBRATION.md` and
`docs/snapshots/2026-08-24_STANDALONE_ENGINE_FINAL_CALIBRATION.md`.
Calibration JSON is under `dataset/mvp-v0.2/calibration/` and is not loaded by
the API. These figures test deterministic behavior on synthetic fixtures. They
do not validate real-world automotive data, market coverage, provider quality,
or purchase outcomes. The dataset remains mock data until reviewed sources
replace it.
