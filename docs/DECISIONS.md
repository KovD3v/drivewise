# DriveWise decision records

## ADR-001: LLM does not determine ranking

**Status:** Accepted

Deterministic Advisor code produces recommendations and ranking. Generative AI
may interpret free-form input and explain output, but it must not recalculate or
override the ranking.

## ADR-002: Decision Score is contextual

**Status:** Accepted

Decision Score belongs to the relationship `user` and `vehicle`. It is not an
absolute rating stored on the vehicle.

## ADR-003: Decision Confidence is separate from Decision Score

**Status:** Accepted

Decision Confidence describes profile completeness, evidence completeness, and
ranking stability. It is not a probability of purchase success.

## ADR-004: Advisor v3 score composition

**Status:** Accepted

Advisor v3 uses:

- 65% Structural Fit
- 35% Preference Fit
- Preference rank weights of 50%, 30%, and 20% for the first three priorities

Structural Fit has six stable pillars. Priorities affect Preference Fit only so
the same preference is not counted twice.

## ADR-005: Hard and soft constraints

**Status:** Accepted

Requests declare constraint modes. A hard constraint can exclude a candidate. A
soft constraint affects fit and is reported as a trade-off. Missing required
evidence returns `insufficient_data` rather than a guessed value.

## ADR-006: Garage can be a hard constraint

**Status:** Accepted

Advisor checks useful length, body width, height, door height, and door width
against width with mirrors folded. A hard incompatible fit excludes a vehicle.
A tight but possible fit remains scoreable and is explained. Missing dimensions
block a definitive fit claim.

## ADR-007: Source evidence has confidence and freshness

**Status:** Accepted

Evidence records retain source identity, observation time, record time, content
hash, current state, and supported metrics. Ranking uses current claims from
permitted sources. Specialist assessments must also identify exact
applicability and a module version.

## ADR-008: The frontend is a client

**Status:** Accepted

The web app does not reproduce Advisor formulas. It calls the API and renders
the response. The API is the only runtime boundary for ranking.

## ADR-009: Backend owns the integration boundary

**Status:** Accepted

FastAPI owns HTTP, validation, persistence, and session orchestration. The
Advisor service owns deterministic eligibility, module assessment, scoring,
and ranking. Database and transport concerns do not enter scoring modules.

## ADR-010: Vehicle pages explain decisions

**Status:** Accepted

Technical specifications support the decision context. The page also exposes
fit, reasons, trade-offs, ownership estimates, evidence, and missing data.

## ADR-011: Mock data is not production truth

**Status:** Accepted

Dataset v0.2 and its calibration material are synthetic development fixtures.
The product must label them as mock data until reviewed sources replace them.

## ADR-012: Advisor v3 is the single ranking authority

**Status:** Accepted

The retired `decision_engine/` package is not a compatibility runtime. Its
reports are historical snapshots and its calibration JSON is non-runtime
dataset material. API and Guided Decision use `advisor-v3.0`.
