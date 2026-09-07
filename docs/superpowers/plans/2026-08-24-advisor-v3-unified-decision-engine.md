# Advisor v3 unified decision engine implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two Drivewise ranking implementations with one backward-compatible `advisor-v3.0` runtime that preserves Advisor v2 trust controls and implements every Decision Engine v1 capability.

**Architecture:** Integrate Vehicle Knowledge Profile and Guided Decision first. Add deterministic Advisor modules that return versioned assessments, then make `scoring.py` the only orchestrator for eligibility, six-pillar Structural Fit, ordered Preference Fit, confidence, explanations, and persistence. Retire the standalone runtime only after its useful behavior is covered by integrated tests.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, psycopg 3, PostgreSQL/pgvector, pytest, Ruff, Bun, React, TanStack Start, Vitest.

**Spec:** `docs/superpowers/specs/2026-08-24-advisor-v3-unified-decision-engine-design.md`

## Global constraints

- `advisor-v3.0` is the only production ranking implementation.
- Keep `POST /advisor/recommendations` backward compatible with v2 request and response fields.
- Preserve exact vehicle, spec, and offer identity, source permission, review, freshness, and provenance gates.
- No LLM may calculate scores, select constraints, or choose the next question.
- Missing data produces `insufficient_data`; never substitute a neutral score.
- Estimated values include a version and named assumptions.
- No frontend redesign and no new dependency without measured need.
- Use Bun for frontend commands.
- Add tests before each new runtime behavior and observe the expected failure.
- Preserve the dirty main checkout. Work only in `.worktrees/advisor-v3-unified-engine`.

## File map

- `apps/api/app/services/advisor/decision.py`: shared assessment values.
- `apps/api/app/services/advisor/constraints.py`: hard and soft constraints.
- `apps/api/app/services/advisor/tco.py`: annual TCO estimate.
- `apps/api/app/services/advisor/garage.py`: fail-closed geometry.
- `apps/api/app/services/advisor/powertrain.py`: extended powertrain fit.
- `apps/api/app/services/advisor/safety.py`: safety assessment.
- `apps/api/app/services/advisor/reliability.py`: reliability contract.
- `apps/api/app/services/advisor/vehicle_dna.py`: DNA contract.
- `apps/api/app/services/advisor/issues.py`: known-issue applicability.
- `apps/api/app/services/advisor/recalls.py`: recall applicability.
- `apps/api/app/services/advisor/confidence.py`: confidence signal.
- `apps/api/app/services/advisor/scoring.py`: sole ranking orchestrator.
- `apps/api/tests/test_advisor_decision_modules.py`: fit and TCO modules.
- `apps/api/tests/test_advisor_assessments.py`: specialist contracts.
- `apps/api/tests/test_advisor_v3_scoring.py`: v3 composition gold cases.

---

### Task 1: Integrate Vehicle Knowledge Profile

**Files:**
- Integrate commits: `0090f23`, `4744d5c`, `e04a736`, `5a86347`, `130f237`, `b57a1c1`, `10db6da`, `8d14970`, `fedee26`
- Verify: `apps/api/tests/test_catalog_import.py`
- Verify: `apps/api/tests/test_vehicle_listing_api.py`
- Verify: `apps/api/tests/test_migrations.py`

**Interfaces:**
- Consumes: schema through `0004_curated_catalog.sql`.
- Produces: migration `0005_vehicle_knowledge_profile.sql`, `VehicleSpecDetail`, curated profile ingestion, and source-aware reads.

- [ ] **Step 1: Confirm the integration payload**

```bash
git diff --name-status origin/main...origin/feat/vehicle-knowledge-profile
git log --oneline origin/main..origin/feat/vehicle-knowledge-profile
```

Expected: the nine listed functional commits are present.

- [ ] **Step 2: Cherry-pick the reviewed sequence**

```bash
git cherry-pick 0090f23 4744d5c e04a736 5a86347 130f237 b57a1c1 10db6da 8d14970 fedee26
```

- [ ] **Step 3: Run focused tests and Ruff**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_catalog_import.py apps/api/tests/test_vehicle_listing_api.py apps/api/tests/test_migrations.py -q
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m ruff check apps/api
git status --short --branch
```

Expected: tests and Ruff pass; database-only cases may skip.

---

### Task 2: Port the Guided Decision baseline

**Files:**
- Create: `apps/api/app/api/routers/guided_decisions.py`
- Create: `apps/api/app/repositories/guided_decisions.py`
- Create: `apps/api/app/schemas/guided_decisions.py`
- Create: `apps/api/app/services/guided_decisions/`
- Create: `apps/api/migrations/0006_guided_decisions.sql`
- Create: `apps/api/tests/test_guided_decisions.py`
- Create: `docs/guided-decision-contract.md`
- Modify: `apps/api/app/api/dependencies.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_migrations.py`
- Modify: `docs/api-contract.md`, `docs/architecture.md`, `docs/data-model.md`

**Interfaces:**
- Consumes: `score_recommendations()`, `AdvisorRepository`, and migration `0005`.
- Produces: create, turn, and reopen endpoints plus `guided-decision-v1` optimistic-concurrency persistence.

- [ ] **Step 1: Port existing tests before production code**

Port `apps/api/tests/test_guided_decisions.py` from the main checkout. Preserve this contract assertion:

```python
def test_guided_decision_api_uses_camel_case_contract_and_versioning(client):
    response = client.post(
        "/guided-decisions",
        json={"message": "Cerco un SUV per la famiglia con 35000 euro"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["contractVersion"] == "guided-decision-v1"
    assert payload["profileVersion"] == 1
    assert payload["decisionProfile"]["budgetEur"]["value"] == 35000
```

- [ ] **Step 2: Verify RED**

Run: `/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_guided_decisions.py -q`

Expected: collection fails because `app.schemas.guided_decisions` is absent.

- [ ] **Step 3: Port the reviewed implementation**

Port the listed files from the main checkout, reconciling only Vehicle Knowledge Profile types. Preserve the exact callables `process_guided_decision_turn(*, decision_id: UUID, profile_version: int, current_profile: DecisionProfile, message: str, advisor_repository, as_of: datetime) -> GuidedDecisionEngineResult` and `evaluate_garage_compatibility(profile: DecisionProfile, *, vehicle_id: UUID, spec_id: UUID, vehicle_dimensions: VehicleDimensions) -> GarageCompatibility | None`.

- [ ] **Step 4: Verify GREEN**

Run: `/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_guided_decisions.py apps/api/tests/test_advisor_api.py apps/api/tests/test_migrations.py -q`

- [ ] **Step 5: Commit**

```bash
git add -- apps/api docs/guided-decision-contract.md docs/api-contract.md docs/architecture.md docs/data-model.md
git commit -m "feat(api): add stateful guided decisions"
```

---

### Task 3: Define v3 request and assessment contracts

**Files:**
- Create: `apps/api/app/services/advisor/decision.py`
- Create: `apps/api/tests/test_advisor_decision_modules.py`
- Modify: `apps/api/app/schemas/advisor.py`
- Modify: `apps/api/app/schemas/guided_decisions.py`

**Interfaces:**
- Consumes: Advisor v2 models.
- Produces: `ModuleAssessment`, constraint modes, garage request, expanded priorities, and compatible response additions.

- [ ] **Step 1: Write failing tests**

```python
def test_v2_request_defaults_to_single_usage_and_soft_preferences():
    request = AdvisorRecommendationRequest(
        budget_max_eur=30_000,
        primary_use="family",
        preferred_body_style="suv",
    )
    assert request.usage == ["family"]
    assert request.constraint_modes.body_style == "soft"

def test_insufficient_assessment_rejects_a_value():
    with pytest.raises(ValueError):
        ModuleAssessment(
            status="insufficient_data",
            version="reliability-v1",
            value=70,
        )
```

- [ ] **Step 2: Verify RED**

Run: `/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_decision_modules.py -q`

- [ ] **Step 3: Implement shared values and request additions**

```python
ModuleStatus = Literal["available", "estimated", "insufficient_data"]

@dataclass(frozen=True)
class ModuleAssessment:
    status: ModuleStatus
    version: str
    value: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    evidence: tuple[dict[str, Any], ...] = ()
    missing_data: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status == "insufficient_data" and self.value is not None:
            raise ValueError("insufficient_data cannot carry a value")

class AdvisorConstraintModes(BaseModel):
    budget: Literal["hard", "soft"] = "soft"
    body_style: Literal["hard", "soft"] = "soft"
    fuel_type: Literal["hard", "soft"] = "soft"
    transmission: Literal["hard", "soft"] = "soft"
    garage: Literal["hard", "soft"] = "soft"
```

Add optional `usage`, `children_count`, `passengers_usual`, `garage`, `automatic_required`, and `constraint_modes`. Normalize absent usage to `[primary_use]` and reject duplicates.

- [ ] **Step 4: Add backward-compatible response fields**

Add defaulted `decision_status`, `decision_score`, `decision_confidence`, `structural_fit`, `preference_fit`, `pillar_scores`, `penalties`, `strengths`, `missing_factors`, `module_versions`, and `score_composition`. Expand `AdvisorPriority` with every v1 priority.

- [ ] **Step 5: Verify and commit**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_decision_modules.py apps/api/tests/test_advisor_scoring.py apps/api/tests/test_advisor_api.py -q
git add -- apps/api/app/services/advisor/decision.py apps/api/app/schemas apps/api/tests/test_advisor_decision_modules.py
git commit -m "feat(api): define Advisor v3 decision contracts"
```

---

### Task 4: Assemble source-aware decision inputs

**Files:**
- Modify: `apps/api/app/repositories/advisor.py`
- Modify: `apps/api/tests/test_advisor_api.py`

**Interfaces:**
- Consumes: migration `0005` tables and current candidate shape.
- Produces: candidate `decision_context` without removing v2 keys.

- [ ] **Step 1: Write a failing repository test**

```python
context = candidate["decision_context"]
assert context["dimensions"]["length_mm"] == 4189
assert context["powertrain"]["power_kw"] == 96.0
assert context["safety"]["ratings"][0]["overall_stars"] == 5
assert context["safety"]["ratings"][0]["source_url"].startswith("https://")
```

- [ ] **Step 2: Verify RED**

Run: `/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_api.py -q`

Expected: missing `decision_context`.

- [ ] **Step 3: Extend query and mapper**

```python
candidate["decision_context"] = {
    "identity": {
        "generation_name": row["generation_name"],
        "restyling_label": row["restyling_label"],
        "category": row["category"],
    },
    "dimensions": {
        "length_mm": row["length_mm"],
        "body_width_mm": row["width_mm"],
        "height_mm": row["height_mm"],
        "width_mirrors_folded_mm": None,
        "curb_weight_kg": row["curb_weight_kg"],
    },
    "powertrain": {
        "engine_code": row["engine_code"],
        "power_kw": row["power_kw"],
        "fuel_type": row["spec_fuel_type"],
        "transmission_type": row["transmission_type"],
    },
    "performance": {
        "acceleration_0_100_s": row["acceleration_0_100_s"],
        "top_speed_kmh": row["top_speed_kmh"],
        "braking_100_0_m": row["braking_100_0_m"],
    },
    "maintenance": row["maintenance_items"],
    "safety": {"ratings": row["safety_ratings"], "features": row["safety_features"]},
    "technology_comfort": row["technology_comfort_features"],
}
```

Every child retains source name, URL, and observed date. Do not add mock reliability, issues, recalls, or DNA.

- [ ] **Step 4: Verify and commit**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_api.py apps/api/tests/test_catalog_import.py -q
git add -- apps/api/app/repositories/advisor.py apps/api/tests/test_advisor_api.py
git commit -m "feat(api): assemble Advisor decision inputs"
```

---

### Task 5: Implement estimated TCO

**Files:**
- Create: `apps/api/app/services/advisor/tco.py`
- Modify: `apps/api/tests/test_advisor_decision_modules.py`
- Modify: `apps/api/app/services/advisor/model_analysis.py`

**Interfaces:**
- Consumes: offer price, annual kilometres, consumption, power, model year, condition, mileage, and MIMIT/ARERA prices.
- Produces: `estimate_tco(request, candidate, as_of) -> ModuleAssessment` with energy, insurance, tax, maintenance, tyres, depreciation, and total.

- [ ] **Step 1: Write failing tests**

```python
def test_tco_returns_a_versioned_full_estimate(candidate):
    result = estimate_tco(v3_request(annual_km=15_000), candidate, as_of=AS_OF)
    assert result.status == "estimated"
    assert result.version == "tco-v1"
    annual = result.details["annual_eur"]
    assert set(annual) == {
        "energy", "insurance", "tax", "maintenance",
        "tyres", "depreciation", "total",
    }
    assert annual["total"] == sum(value for key, value in annual.items() if key != "total")
    assert result.assumptions

def test_tco_fails_closed_without_consumption(candidate):
    candidate["spec"]["consumption_l_100km"] = None
    result = estimate_tco(v3_request(), candidate, as_of=AS_OF)
    assert result.status == "insufficient_data"
    assert "consumption" in result.missing_data
```

- [ ] **Step 2: Verify RED**

Run the two tests. Expected: import failure for `advisor.tco`.

- [ ] **Step 3: Implement `estimate_tco`**

Define `TCO_VERSION = "tco-v1"` and implement the exact callable `estimate_tco(request: AdvisorRecommendationRequest, candidate: dict[str, Any], *, as_of: datetime) -> ModuleAssessment`.

Use these versioned assumptions:

- insurance: EUR 650 plus 0.8 percent of offer price, capped at EUR 1,600;
- tax: zero for electric, otherwise EUR 2.58 per kW through 100 kW and EUR 3.87 above 100; absent power stays missing;
- maintenance: reuse the Model Analysis age, mileage, body, and powertrain heuristic;
- tyres: EUR 180 city/small hatchback, EUR 240 hatchback/sedan/wagon, EUR 300 crossover/SUV/MPV/van;
- depreciation: 9.333 percent of offer price annually, matching the current 28 percent three-year estimate;
- energy: exact consumption times MIMIT or ARERA rate and annual kilometres.

Missing energy returns `insufficient_data`. A missing non-energy component is omitted, named in `missing_data`, and leaves status `estimated`.

- [ ] **Step 4: Verify and commit**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_decision_modules.py apps/api/tests/test_model_analysis_api.py -q
git add -- apps/api/app/services/advisor/tco.py apps/api/app/services/advisor/model_analysis.py apps/api/tests/test_advisor_decision_modules.py
git commit -m "feat(api): add versioned TCO estimates"
```

---

### Task 6: Implement constraints, family fit, and garage fit

**Files:**
- Create: `apps/api/app/services/advisor/constraints.py`
- Create: `apps/api/app/services/advisor/garage.py`
- Modify: `apps/api/tests/test_advisor_decision_modules.py`

**Interfaces:**
- Consumes: expanded request and `decision_context`.
- Produces: `ConstraintEvaluation`, `family_fit()`, and `garage_fit()`.

- [ ] **Step 1: Write failing tests**

```python
def test_passenger_constraint_excludes_insufficient_seats(candidate):
    candidate["spec"]["seats"] = 4
    result = evaluate_constraints(v3_request(passengers_usual=5), candidate)
    assert result.status == "excluded"
    assert result.reasons == ("insufficient_seats",)

def test_hard_garage_fails_closed_without_folded_width(candidate):
    request = v3_request(garage=complete_garage(), garage_mode="hard")
    result = evaluate_constraints(request, candidate)
    assert result.status == "insufficient_data"
    assert "vehicle.width_mirrors_folded_mm" in result.missing_data

def test_family_fit_uses_versioned_cargo_target(candidate):
    result = family_fit(children_count=2, passengers_usual=4, candidate=candidate)
    assert result.version == "family-fit-v1"
    assert result.details["cargo_target_liters"] == 400
```

- [ ] **Step 2: Verify RED**

Expected: import failures for `constraints` and `garage`.

- [ ] **Step 3: Implement constraints**

Add a frozen `ConstraintEvaluation` dataclass with `status: Literal["eligible", "excluded", "insufficient_data"]`, tuple fields `reasons`, `missing_data`, and `soft_tradeoffs`, and implement `evaluate_constraints(request: AdvisorRecommendationRequest, candidate: dict[str, Any]) -> ConstraintEvaluation`.

Use stable order: condition, exact hard budget, mileage, passengers, body style, fuel, transmission, garage. Existing market, source, freshness, and identity eligibility remains in `scoring.py`.

- [ ] **Step 4: Implement family and garage modules**

Cargo target is `min(550, 250 + 75 * children_count)`. Garage compares internal body width separately from folded-mirror entrance width. Any missing required measure is `insufficient_data`, never zero.

- [ ] **Step 5: Verify and commit**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_decision_modules.py -q
git add -- apps/api/app/services/advisor/constraints.py apps/api/app/services/advisor/garage.py apps/api/tests/test_advisor_decision_modules.py
git commit -m "feat(api): add v3 constraints and fit checks"
```

---

### Task 7: Implement extended powertrain fit

**Files:**
- Create: `apps/api/app/services/advisor/powertrain.py`
- Modify: `apps/api/app/schemas/advisor.py`
- Modify: `apps/api/app/services/advisor/energy_prices.py`
- Modify: `apps/api/tests/test_advisor_decision_modules.py`
- Modify: `apps/api/tests/test_advisor_scoring.py`

**Interfaces:**
- Consumes: usage, annual kilometres, fuel type, consumption, range, and charging context.
- Produces: `powertrain_fit() -> ModuleAssessment` for all recognized types.

- [ ] **Step 1: Write a failing parametrized test**

```python
@pytest.mark.parametrize(
    "fuel_type",
    [
        "petrol", "diesel", "mild_hybrid_petrol",
        "full_hybrid_petrol", "plug_in_hybrid_petrol",
        "electric", "petrol_lpg",
    ],
)
def test_powertrains_are_assessed_not_legacy_excluded(fuel_type, candidate):
    candidate["spec"]["fuel_type"] = fuel_type
    result = powertrain_fit(v3_request(), candidate)
    assert result.status in {"available", "estimated", "insufficient_data"}
    assert result.version == "powertrain-fit-v1"
```

Add a regression that PHEV does not produce `unsupported_phev`.

- [ ] **Step 2: Verify RED**

Expected: Pydantic rejects PHEV and current eligibility excludes it.

- [ ] **Step 3: Implement fuel support and thresholds**

Add `plug_in_hybrid_petrol`. PHEV needs liquid consumption, electric consumption, electric range, and charging context; missing context is `insufficient_data`. EV highway range affects fit but is not a fixed hard exclusion. LPG uses its MIMIT rate. Port the useful v1 city/highway and distance rules, expose thresholds, and clamp results to 0 through 100.

- [ ] **Step 4: Verify and commit**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_decision_modules.py apps/api/tests/test_advisor_scoring.py -q
git add -- apps/api/app/services/advisor/powertrain.py apps/api/app/services/advisor/energy_prices.py apps/api/app/schemas/advisor.py apps/api/tests/test_advisor_decision_modules.py apps/api/tests/test_advisor_scoring.py
git commit -m "feat(api): assess extended powertrain types"
```

---

### Task 8: Add specialist assessment modules

**Files:**
- Create: `apps/api/app/services/advisor/safety.py`
- Create: `apps/api/app/services/advisor/reliability.py`
- Create: `apps/api/app/services/advisor/vehicle_dna.py`
- Create: `apps/api/app/services/advisor/issues.py`
- Create: `apps/api/app/services/advisor/recalls.py`
- Create: `apps/api/tests/test_advisor_assessments.py`

**Interfaces:**
- Consumes: `decision_context` and future explicit specialist inputs.
- Produces: versioned assessments and capped penalties, never rankings.

- [ ] **Step 1: Write failing tests**

```python
def test_safety_uses_ratings_and_provenance(candidate):
    result = assess_safety(candidate)
    assert result.status == "available"
    assert result.version == "safety-v1"
    assert 0 <= result.value <= 100
    assert result.evidence

def test_reliability_without_input_is_insufficient(candidate):
    result = assess_reliability(candidate)
    assert result.status == "insufficient_data"
    assert result.missing_data == ("reliability_assessment",)

def test_issue_penalizes_only_matching_variant(candidate):
    assert known_issue_penalty(candidate, [issue_input(engine_code="OTHER")]).value == 0
    engine_code = candidate["decision_context"]["powertrain"]["engine_code"]
    assert known_issue_penalty(candidate, [issue_input(engine_code=engine_code)]).value > 0

def test_unknown_recall_applicability_warns_without_penalty(candidate):
    result = recall_penalty(candidate, [recall_input(applicability="unknown")])
    assert result.value == 0
    assert "recall_applicability" in result.missing_data
```

- [ ] **Step 2: Verify RED**

Expected: imports fail for all five modules.

- [ ] **Step 3: Implement exact signatures**

Implement the exact callables `assess_safety(candidate) -> ModuleAssessment`, `assess_reliability(candidate) -> ModuleAssessment`, `assess_vehicle_dna(candidate) -> dict[str, ModuleAssessment]`, `known_issue_penalty(candidate, issues) -> ModuleAssessment`, and `recall_penalty(candidate, recalls) -> ModuleAssessment`.

Safety averages available rating percentages and uses stars only when percentages are absent. Reliability and DNA consume explicit inputs or return `insufficient_data`. DNA may expose feature evidence but cannot turn feature count into a universal score.

- [ ] **Step 4: Implement applicability before severity**

Issues match generation, spec, engine, transmission, and production year. Conflicts mean not applicable; missing applicability means unknown. Recalls distinguish open, resolved, and unknown. Cap issue penalty at 8 and recall penalty at 6.

- [ ] **Step 5: Verify and commit**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_assessments.py -q
git add -- apps/api/app/services/advisor/safety.py apps/api/app/services/advisor/reliability.py apps/api/app/services/advisor/vehicle_dna.py apps/api/app/services/advisor/issues.py apps/api/app/services/advisor/recalls.py apps/api/tests/test_advisor_assessments.py
git commit -m "feat(api): add v3 assessment modules"
```

---

### Task 9: Compose pillars, preferences, confidence, and explanations

**Files:**
- Create: `apps/api/app/services/advisor/confidence.py`
- Create: `apps/api/tests/test_advisor_v3_scoring.py`
- Modify: `apps/api/app/services/advisor/scoring.py`
- Modify: `apps/api/tests/test_advisor_scoring.py`

**Interfaces:**
- Consumes: Tasks 3 through 8 module outputs and existing exact eligibility.
- Produces: `score_recommendations()` with `advisor-v3.0`, six pillars, 65/35 composition, ordered preferences, confidence, explanations, and stable ranking.

- [ ] **Step 1: Write failing composition tests**

```python
def test_v3_composes_structural_and_preference_fit_exactly():
    item = score_one(complete_candidate(), priorities=["reliability", "running_cost", "comfort"])
    assert item.structural_fit == 80.0
    assert item.preference_fit == 90.0
    assert item.decision_score == 83.5
    assert item.score == item.decision_score

def test_priority_order_does_not_change_structural_fit():
    first = score_one(complete_candidate(), priorities=["safety", "technology", "comfort"])
    second = score_one(complete_candidate(), priorities=["comfort", "technology", "safety"])
    assert first.structural_fit == second.structural_fit
    assert first.preference_fit != second.preference_fit

def test_missing_preference_returns_provisional_legacy_score():
    item = score_one(candidate_without_reliability(), priorities=["reliability"])
    assert item.decision_status == "insufficient_data"
    assert item.decision_score is None
    assert item.score == item.structural_fit
    assert "reliability" in item.missing_factors
```

- [ ] **Step 2: Verify RED**

Expected: the v2 scorer lacks v3 fields and composition.

- [ ] **Step 3: Implement six-pillar orchestration**

```python
PILLAR_WEIGHTS = {
    "economics": 0.266667,
    "practicality": 0.177778,
    "reliability_safety": 0.222222,
    "driving": 0.111111,
    "technology": 0.111111,
    "powertrain_fit": 0.111111,
}
PREFERENCE_WEIGHTS = (0.50, 0.30, 0.20)
```

Keep eligibility in `scoring.py`, call the modules once per candidate, renormalize only available factors, and require Economics plus Practicality for a provisional score. Priorities affect only Preference Fit.

Use the v1 subfactor composition, excluding and renormalizing unavailable subfactors:

```python
PILLAR_COMPONENTS = {
    "economics": {"price_fit": 0.45, "tco": 0.40, "running_cost": 0.15},
    "practicality": {
        "category_fit": 0.22,
        "usage_fit": 0.33,
        "family_fit": 0.25,
        "garage_fit": 0.20,
    },
    "reliability_safety": {"reliability": 0.58, "safety": 0.42},
    "driving": {"comfort": 0.48, "sport": 0.22, "travel": 0.30},
    "technology": {"technology": 1.0},
    "powertrain_fit": {"powertrain_fit": 1.0},
}
```

`usage_fit` averages every value in `request.usage`. Known-issue and recall penalties apply to Structural Fit before final composition and remain capped at 8 and 6.

Map Preference Fit directly:

```python
PRIORITY_METRIC = {
    "price": "price_fit",
    "budget": "price_fit",
    "running_cost": "tco",
    "space": "family_fit",
    "family": "family_fit",
    "reliability": "reliability",
    "safety": "safety",
    "comfort": "comfort",
    "performance": "sport",
    "technology": "technology",
    "efficiency_range": "powertrain_fit",
    "powertrain_fit": "powertrain_fit",
}
```

- [ ] **Step 4: Implement confidence**

```python
def decision_confidence(
    *,
    profile_completeness: float,
    evidence_completeness: float,
    ranking_stability: float,
) -> ModuleAssessment:
    value = profile_completeness * 0.45 + evidence_completeness * 0.35 + ranking_stability * 0.20
    return ModuleAssessment(
        status="available",
        version="decision-confidence-v1",
        value=round(max(0.0, min(100.0, value)), 1),
        details={
            "profile_completeness": profile_completeness,
            "evidence_completeness": evidence_completeness,
            "ranking_stability": ranking_stability,
        },
    )
```

Defaults reduce profile completeness. Estimated modules contribute less than sourced modules. Ranking stability uses the within-group score gap.

- [ ] **Step 5: Preserve deterministic explanations and ranking**

Sort complete before provisional, then effective score, confidence, price, mileage, listing reference, and listing ID. Populate strengths, trade-offs, penalties, missing factors, module versions, assumptions, and evidence.

Add a test module that raises a controlled exception. The candidate must remain provisional, the affected factor must become `insufficient_data`, and no neutral score may be inserted. Preserve transactional persistence tests proving a failed item write cannot mark a run complete.

- [ ] **Step 6: Verify and commit**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_v3_scoring.py apps/api/tests/test_advisor_scoring.py apps/api/tests/test_advisor_decision_modules.py apps/api/tests/test_advisor_assessments.py -q
git add -- apps/api/app/services/advisor/scoring.py apps/api/app/services/advisor/confidence.py apps/api/tests/test_advisor_v3_scoring.py apps/api/tests/test_advisor_scoring.py
git commit -m "feat(api): unify ranking in Advisor v3"
```

---

### Task 10: Wire API persistence and Guided Decision to v3

**Files:**
- Modify: `apps/api/app/api/routers/advisor.py`
- Modify: `apps/api/app/repositories/advisor.py`
- Modify: `apps/api/app/services/guided_decisions/`
- Modify: `apps/api/app/schemas/guided_decisions.py`
- Modify: `apps/api/tests/test_advisor_api.py`
- Modify: `apps/api/tests/test_guided_decisions.py`

**Interfaces:**
- Consumes: unified `score_recommendations()` and v3 models.
- Produces: persisted v3 breakdown and a richer stateful profile without a new scoring table.

- [ ] **Step 1: Write failing API and persistence tests**

```python
def test_post_advisor_persists_v3_breakdown(client, repository):
    payload = client.post("/advisor/recommendations", json=v2_payload()).json()
    assert payload["scoring_version"] == "advisor-v3.0"
    item = payload["groups"][0]["items"][0]
    assert "structural_fit" in item
    assert "decision_confidence" in item
    stored = repository.saved_items[0]["score_breakdown"]
    assert stored["module_versions"]

def test_guided_profile_collects_family_and_constraints(client):
    payload = create_guided_decision(
        client,
        "Siamo in cinque con tre figli, città e autostrada, automatico obbligatorio",
    )
    profile = payload["decisionProfile"]
    assert profile["childrenCount"]["value"] == 3
    assert profile["passengersUsual"]["value"] == 5
    assert profile["automaticRequired"]["value"] is True
```

- [ ] **Step 2: Verify RED**

Expected: API reports v2 and Guided profile lacks the new facts.

- [ ] **Step 3: Persist v3 breakdown**

Use `recommendation_items.score_breakdown` JSONB for structural fit, preference fit, confidence components, pillars, penalties, missing factors, module versions, assumptions, evidence, and provenance. Store normalized profile and active versions in `recommendation_runs.request_payload`.

- [ ] **Step 4: Extend Guided Decision**

Add typed facts and deterministic questions for usage, children, passengers, automatic requirement, and constraint modes. Parse only explicit Italian signals. Map to one `AdvisorRecommendationRequest`; do not rank inside Guided Decision.

- [ ] **Step 5: Verify and commit**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests/test_advisor_api.py apps/api/tests/test_guided_decisions.py apps/api/tests/test_migrations.py -q
git add -- apps/api/app/api/routers/advisor.py apps/api/app/repositories/advisor.py apps/api/app/services/guided_decisions apps/api/app/schemas/guided_decisions.py apps/api/tests/test_advisor_api.py apps/api/tests/test_guided_decisions.py
git commit -m "feat(api): expose and persist Advisor v3"
```

---

### Task 11: Retire the standalone runtime and document prerequisites

**Files:**
- Delete: `decision_engine/drivewise_engine/`, `decision_engine/demo.py`, `decision_engine/tests/`, `decision_engine/requirements.txt`
- Move: calibration reports to `docs/snapshots/`
- Create: `docs/advisor-v3.md`
- Modify: `docs/api-contract.md`, `docs/architecture.md`, `docs/data-model.md`
- Modify: `docs/CURRENT_STATUS.md`, `docs/DECISIONS.md`, `docs/DECISION_ENGINE_INTEGRATION.md`

**Interfaces:**
- Consumes: completed v3 runtime and green parity tests.
- Produces: one ranking authority and durable prerequisite documentation.

- [ ] **Step 1: Map every v1 module to a green v3 test**

```text
engine.py, preference.py -> test_advisor_v3_scoring.py
confidence.py, data_quality.py -> test_advisor_v3_scoring.py
filters.py, garage.py, powertrain.py, tco.py -> test_advisor_decision_modules.py
penalties.py -> test_advisor_assessments.py
explainability.py, tradeoffs.py -> test_advisor_v3_scoring.py
```

Do not delete an old module until its mapped test passes.

- [ ] **Step 2: Move history and remove the second runtime**

Use `git mv` for calibration reports. Keep `dataset/mvp-v0.2/` with its mock disclaimer. Keep calibration JSON only when an integrated test consumes it; otherwise move it into the dataset as non-runtime material.

- [ ] **Step 3: Document the replacement boundaries**

`docs/advisor-v3.md` covers formula, compatibility, provisional scores, status values, TCO assumptions, Reliability Assessment, Known Issues Registry, Official Recall Resolver, Vehicle DNA Calibration, TCO and valuation providers, folded-mirror dimensions, versions, audit data, and benchmark limits.

- [ ] **Step 4: Check stale runtime claims**

```bash
rg -n "advisor-v2\.0|Decision Engine v1|decision_engine" README.md docs apps/api --glob '*.md' --glob '*.py'
git diff --check
```

Classify every result as historical, compatibility-related, or stale. Remove stale active-runtime claims.

- [ ] **Step 5: Verify and commit**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests -q
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m ruff check apps/api
git add -A -- decision_engine dataset/mvp-v0.2 docs
git commit -m "docs: make Advisor v3 the single decision engine"
```

---

### Task 12: Full-stack verification, review, and PR preparation

**Files:**
- Verify all changed files.
- Modify only when a failing gate reveals a scoped defect.

**Interfaces:**
- Consumes: Tasks 1 through 11.
- Produces: fresh PR evidence and a clean feature branch.

- [ ] **Step 1: Run complete static and unit gates**

```bash
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m pytest apps/api/tests -q
/Users/kovd3v/Documents/Projects/drivewise/apps/api/.venv/bin/python -m ruff check apps/api
bun run test:web
bun run typecheck:web
bun run build:web
git diff origin/main...HEAD --check
```

Expected: zero failures. The existing frontend retry test may print its known route warning but must pass.

- [ ] **Step 2: Run disposable PostgreSQL verification**

Create a fresh `pgvector/pgvector:pg16` database, apply migrations `0001` through `0007`, import `data/fixtures/catalog/catalog-v1.synthetic.json`, rerun the identical import, and run PostgreSQL tests. Do not reuse a database with recommendation runs.

Expected: migrations through `0007`, first import completed, second import unchanged, all integration tests pass.

- [ ] **Step 3: Run API and browser smoke**

Start FastAPI and Vite against the disposable database. Verify `/ready`, `POST /advisor/recommendations` reports `advisor-v3.0`, `/advisor` renders new and used groups, exact evidence remains, and the persisted run contains v3 breakdown. Use the product-native collaborative browser first and record the run ID.

- [ ] **Step 4: Review the complete diff**

```bash
git diff --stat origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
```

Check every spec goal, non-goal, completion criterion, and test requirement. Fix Critical and Important findings.

- [ ] **Step 5: Repeat final verification after review fixes**

Repeat Step 1 and every focused test affected by fixes. Earlier green output is not sufficient.

- [ ] **Step 6: Prepare the PR body**

```markdown
## Summary
- unify Advisor v2 and Decision Engine v1 in advisor-v3.0
- preserve exact-offer provenance and v2-compatible contracts
- add all v1 capabilities with fail-closed missing-data behavior
- document specialist prerequisites and the estimated TCO replacement

## Compatibility
- existing request and response fields remain
- score is provisional Structural Fit only when decisionStatus is insufficient_data

## Verification
- backend tests: report the exact fresh passed and skipped counts
- Ruff: pass
- frontend tests: report the exact fresh passed count
- typecheck: pass
- build: pass
- disposable PostgreSQL: pass
- browser smoke: pass
```

Do not push or open the PR until final verification and review are green.
