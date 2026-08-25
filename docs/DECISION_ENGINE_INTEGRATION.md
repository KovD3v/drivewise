# DriveWise Advisor integration

## Runtime

```text
Web app or Guided Decision
          |
          | HTTPS / JSON
          v
FastAPI backend
  | validation, session state, persistence
  v
Advisor v3 service
  | apps/api/app/services/advisor/scoring.py
  +-- constraints and Garage Fit
  +-- TCO estimate
  +-- powertrain, safety, confidence
  +-- specialist adapters
  v
Reviewed vehicle, spec, offer, and provenance records
```

`POST /advisor/recommendations` and Guided Decision previews use the same
`advisor-v3.0` scorer. The retired `decision_engine/` package is not callable.
The historical calibration reports are in `docs/snapshots/`; their JSON is
non-runtime material under `dataset/mvp-v0.2/calibration/`.

## Boundary rules

- The web app does not copy scoring formulas.
- FastAPI validates requests, coordinates sessions, writes audit records, and
  returns response DTOs.
- Advisor v3 owns eligibility, hard and soft constraints, module assessment,
  scoring, penalties, confidence, explainability, and deterministic ranking.
- The catalog supplies exact vehicle, variant, offer, and provenance identity.
- LLM services may extract profile facts or explain a result. They cannot rank
  or override the scorer.

## What runs now

- `advisor-v3.0` scoring with six structural pillars and the 65/35 composition.
- Ordered preference alignment with 50/30/20 weights.
- Hard and soft constraints, passenger and family rules, and Garage Fit.
- Powertrain Fit for petrol, diesel, mild hybrid, full hybrid, plug-in hybrid,
  electric, and LPG.
- Safety from Vehicle Knowledge Profile data when present.
- Versioned estimated TCO from fixed energy and cost assumptions.
- Versioned confidence, explanations, penalties, persistence, and ranking.

Reliability, known issues, official recalls, Vehicle DNA, and valuation have
adapters and contracts, but no live provider is claimed. They return
`insufficient_data` without valid, applicable inputs. Folded-mirror dimensions
run when the exact catalog measurement exists. See `docs/advisor-v3.md` for
the input requirements and replacement boundary for each module.

## Compatibility

The request accepts existing Advisor fields. The response keeps legacy fields,
including `score`, `component_scores`, `positive_factors`, `tradeoffs`,
`evidence`, and `provenance`, and adds v3 fields such as `decision_status`,
`decision_score`, `structural_fit`, `preference_fit`, `pillar_scores`,
`penalties`, `missing_factors`, `module_versions`, and `score_composition`.

When Preference Fit or another required factor is unavailable, v3 returns
`decision_status=insufficient_data`, `decision_score=null`, and a provisional
legacy `score` containing Structural Fit. This compatibility value is not a
complete Decision Score.

## First vertical slice

1. The web app or Guided Decision submits a typed Decision Profile.
2. FastAPI validates the request and loads reviewed exact-variant offers.
3. Advisor v3 evaluates constraints and modules.
4. The scorer returns grouped results, exclusions, assumptions, evidence,
   missing data, and stable ordering.
5. FastAPI persists the request and complete item breakdown.
6. The client renders the result and its explanations.

## Replacement work

TCO is the current estimated implementation. A sourced TCO provider replaces
the provider or input data while keeping the `ModuleAssessment` contract and
scoring consumer unchanged. Other specialist providers follow the contracts in
`docs/advisor-v3.md`. None may silently convert missing or ambiguous evidence
into a neutral score.
