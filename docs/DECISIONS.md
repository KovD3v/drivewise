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

## ADR-013: The Advisor evaluates models and offers

**Status:** Accepted (2026-11-24)

The Advisor ranks exact vehicle variants. A variant with no eligible offer is
evaluated as a new vehicle at its list price. An eligible offer adds its own
price, mileage, condition, and freshness to the same evaluation. Offers still
enter ranking only from sources with written authorization, so the product
must recommend models while no such source exists.

## ADR-014: Each vehicle type has its own Advisor module

**Status:** Accepted (2026-11-24)

Cars, motorcycles, and scooters are evaluated by separate Advisor modules,
each with its own questions, required facts, and formulas, behind the same API
boundary. A vehicle type without a module is shown as a catalogue without a
score.

## ADR-015: Manufacturer documents supply list price and cargo volume

**Status:** Accepted (2026-11-24), amended by ADR-019 (2026-11-25)

No open source publishes Italian list prices or cargo volumes. These values
come from the manufacturers' public price lists and technical sheets. Each
value keeps the link to its document, and the source passes the source review
before it affects ranking. ADR-019 defines the first group of cars.

The price shown is the public list price including VAT, not the turnkey price.
When a document prints only the price without VAT, the value is computed from
it and marked as computed. When a document prints only the turnkey price, the
value is that price minus the on-road charge the document states, also marked
as computed. When a registered version is no longer in the
current price list, the nearest current version supplies the price, and the
product says so.

## ADR-016: Two-wheel modules score measurable facts only

**Status:** Accepted (2026-11-24)

The motorcycle and scooter modules score facts that a source measures or
states, such as price, seat height, weight, under-seat storage, displacement,
and power. Hand-written 0–100 indices do not enter ranking until a reviewed
source measures them. The car module already follows this rule.

## ADR-017: The public domain moves when the car module recommends cars

**Status:** Accepted (2026-11-24), amended by ADR-019 (2026-11-25)

The public domain moves to this build when the car module recommends the
first real cars in production. Until their modules exist, motorcycles and
scooters are shown without a score. The web app gets no local scoring bridge,
because ADR-008 keeps ranking in the API.

## ADR-018: An interval consumption is published at its upper value

**Status:** Accepted (2026-11-24)

Open registries give the consumption of many variants as an interval. The read
catalogue publishes the upper value of that interval, and the product says the
figure is the upper value. The rule lives in publication, not in a hand
decision per bundle, so it applies whatever source supplies the interval. The
upper value is chosen so that running costs are not understated.

## ADR-019: The first real dataset is new cars by model and engine

**Status:** Accepted (2026-11-25)

The first real dataset holds new cars of the generation on sale. A catalogue
entry is a model with its engine, not a trim. The list price shown is the price
of the base trim, and the product says so. The number of cars and the list of
models are not fixed. No document named the "twelve cars" of ADR-015 and
ADR-017, so that count is withdrawn.

Used cars are out of the first dataset. The data model must accept them later
without a change to vehicle identity.

Euro NCAP safety replaces "reliability" in the product promise, because no
reviewed source measures reliability. Euro NCAP forbids commercial reuse without
prior permission, so its rating enters ranking only after that permission.

Values that follow from stored facts are computed, not stored. These are the
new-driver power limit, the cost per kilometre, and the road tax. Equipment
waits until after the first release.

## ADR-020: A vehicle is one generation, and each fact has a scope and a type

**Status:** Accepted (2026-11-25)

A vehicle row is one generation of one model in one market. The generation is
required before publication. Body style, phase, and model year leave the
identity key. Each metric declares whether a fact belongs to the generation or
to the variant, and whether its value is a number or a code from a closed list.
One registry file defines every metric.

The reason is that published identity is frozen. Today a generation cannot be
filled after the first publication. The design, its evidence, and its six
delivery steps are in
[the identity and facts design](catalog-identity-and-facts-design.md). Tommaso
reviewed and accepted it on 2026-11-25. No step is built yet.

