# Advisor v3

## Runtime boundary

Advisor v3 is the only ranking runtime. `POST /advisor/recommendations` and
Guided Decision previews call `apps/api/app/services/advisor/scoring.py`.
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
| Safety | Yes, `safety-v1` | Knowledge Profile ratings and features with provenance | Replace the catalog assessment input, not pillar composition |
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
Penalties are applied to Structural Fit before the 65/35 composition and are
capped so the result cannot become negative.

Preference Fit maps the first three ordered priorities to direct metrics with
weights 50%, 30%, and 20%. Missing preference metrics are renormalized across
the available priorities and lower confidence. The scorer never invents a
neutral value for missing data.

The pillar component contracts are:

- Economics: price fit 45%, TCO 40%, running cost 15%.
- Practicality: category 22%, usage 33%, family 25%, garage 20%.
- Reliability and Safety: reliability 58%, safety 42%.
- Driving: comfort 48%, sport 22%, travel 30%.
- Technology: calibrated technology input when available.
- Powertrain Fit: the versioned powertrain assessment.

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

## Specialist input contracts

Every specialist input must identify the exact vehicle applicability, carry a
version, and include evidence. Missing or ambiguous applicability is visible in
the module result and lowers confidence.

| Module | Input contract | Identity and applicability keys | Evidence and status requirements |
| --- | --- | --- | --- |
| Safety Assessment | Ratings and curated safety/ADAS features | Exact variant/spec, assessment system, assessment year, market | Source and observed date on each record; `safety-v1` returns `available` when ratings/features exist and `insufficient_data` otherwise |
| Reliability Assessment | Normalized score, confidence, missing data, details | Generation, exact variant/spec, powertrain where relevant | Dated observations, sample and time window when statistical, source and version; otherwise `insufficient_data` |
| Known Issues Registry | Issue severity/frequency, repair range, applicability | Generation, variant/spec, engine, transmission, production-year bounds | Evidence and observed date; ambiguous applicability is a warning, confirmed issues use capped `known-issues-v1` penalty |
| Official Recall Resolver | Campaign records, status, applicability | Exact vehicle/spec plus campaign identity and market | Official source, campaign date and observed date; `open`, `resolved`, or `unknown` status; unknown applicability is not guessed |
| Vehicle DNA Calibration | Comfort, family, sport, travel, and technology values | Exact generation/spec and calibration scope | Versioned rubric, calibration set, feature evidence, and source; feature count alone is not a score |
| TCO Data Provider | Energy, insurance, tax, maintenance, tyres, depreciation amounts | Market, currency, annual usage, offer/spec, valuation date | Source, observed date, assumptions, and provider version |
| Valuation Provider | Current value and residual value | Exact variant, condition, mileage, market, valuation date | Source, observed date, sample/method, assumptions, and provider version |
| Garage Dimension Provider | Length, body width, height, folded-mirror width | Exact spec and measurement semantics | Source, observed date, units, and whether folded width is measured or inferred |

The current adapters accept explicit `decision_context` assessments. They do
not fetch a provider or turn a missing record into a neutral score.

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
