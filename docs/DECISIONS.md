# DriveWise — Decision Records

## ADR-001 — LLM does not determine ranking
**Status:** Accepted

The recommendation/ranking is produced by deterministic code. Generative AI may interpret free-form input and explain output, but must not silently recalculate or override the ranking.

## ADR-002 — Decision Score is contextual
**Status:** Accepted

Decision Score belongs to the relationship `user ↔ vehicle`; it is not an absolute rating stored on the vehicle.

## ADR-003 — Decision Confidence is separate from Decision Score
**Status:** Accepted

Decision Confidence represents how reliable the recommendation is given profile completeness, data quality and ranking stability.

## ADR-004 — v1.0 score composition
**Status:** Accepted for MVP

Final score composition:
- 65% Structural Fit
- 35% Preference Fit

Top-three user priorities contribute to Preference Fit with rank weights 50% / 30% / 20%.

## ADR-005 — Hard vs soft constraints
**Status:** Accepted

Some preferences may be either soft or hard. Examples: category SUV, fuel type and automatic transmission. A hard constraint may exclude a vehicle before scoring. A soft preference affects fit score instead.

## ADR-006 — Garage can be a hard constraint
**Status:** Accepted

If the vehicle physically cannot pass the garage entrance or fit within required dimensions, it is excluded. Tight but possible fits remain scoreable and are explained as a trade-off.

## ADR-007 — Data sources have different confidence
**Status:** Accepted

Data confidence incorporates source reliability, freshness, field confidence and verification. Manufacturer/official sources rank above community or synthetic sources.

## ADR-008 — Lovable is a client, not the calculation engine
**Status:** Accepted

Do not duplicate the Python scoring rules in Lovable/TypeScript. Lovable calls backend APIs that execute the Python engine.

## ADR-009 — Backend API boundary
**Status:** Accepted

The Python engine must remain an isolated domain package that can be called by FastAPI/service code. HTTP, auth, database and session concerns must not leak into scoring modules.

## ADR-010 — Vehicle page is decision-oriented
**Status:** Accepted

Technical specifications are secondary. The page prioritizes fit, reasons, trade-offs, ownership cost, reliability, known issues, recalls and context-specific insight.

## ADR-011 — Mock data is not production truth
**Status:** Accepted

Current vehicle records are development fixtures. UI should support a subtle `Preview MVP` / demo indicator until real validated sources replace them.
