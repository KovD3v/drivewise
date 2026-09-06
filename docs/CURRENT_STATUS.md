# DriveWise — Current Status

_Last updated: 2026-09-06_

## Overall phase
**MVP implementation — frontend stabilization completed, backend/Decision Engine integration now the main priority.**

DriveWise has moved beyond the initial prototype stage. The product now has a mature public-facing identity, a multi-vehicle decision flow concept, a frozen Decision Engine contract for the MVP, and a functional coverage dataset designed to test Auto, Moto and Scooter scenarios.

## Product / Brand
- Product name: **DriveWise**.
- Public domain purchased: **drivewise-italia.com**.
- Positioning: **Decision Intelligence platform for Auto, Moto and Scooter**, not a traditional vehicle comparator.
- Landing Page redesigned with stronger premium / startup positioning.
- Brand identity consolidated around the current mint/teal visual language.
- Messaging evolved around:
  - Decision Intelligence;
  - proprietary Decision Engine;
  - explainable recommendations;
  - Vehicle Knowledge Base;
  - personalized Decision Score.
- Avoid claims such as “patented” until a patent/application actually exists. Current correct wording: **proprietary Decision Engine / proprietary decision methodology**.

## Current frontend
Lovable prototype/app:
`https://drivewise-decision-hub.lovable.app/`

Public domain:
`https://drivewise-italia.com`

### Implemented / designed
- Landing Page.
- `/app/start` guided decision journey.
- Auto / Moto / Scooter selection concept.
- Personal area (`/app/me`) with future modules / Coming Soon sections.
- Decision Report UI concept.
- Vehicle detail page concept.
- Garage Fit UX.
- Dynamic report concept by vehicle type.
- Premium / animated UX direction aligned to DriveWise brand identity.

### Frontend rules frozen for MVP
- A new analysis must create a **new Decision Session**.
- `/app/start` must not automatically restore the previous demo/simulation.
- No previous ranking, score, confidence, vehicle or garage state should leak into a new analysis.
- `profile_completion` starts from `0`.
- `decision_confidence` starts from `0` and is conceptually different from profile completeness.
- Vehicle flows must be different for:
  - `car`
  - `motorcycle`
  - `scooter`
- Garage must use exactly three states:
  - `known`
  - `unknown_dimensions`
  - `none`
- Garage Fit appears in the final report **only** when `garage_status == known`.
- The final report must not render empty / irrelevant cards.

## Area personale / My DriveWise
The personal area has been designed as the future retention layer of the product.

Planned modules include:
- My Garage
- Decision History
- Wishlist
- Compare Later
- Cost Tracker
- Smart Maintenance
- Vehicle Health
- Document Wallet
- AI Advisor
- Family Garage
- Finance
- Insurance Center
- Community
- Value Prediction
- Upgrade Advisor
- Insights
- Achievement
- Smart Garage

The information architecture has been reorganized into macro-sections rather than a flat catalog of cards. The long-term objective is to accompany the user across the whole vehicle lifecycle, not only during purchase.

## Decision Engine
### Status
- Python Decision Engine iterations v0.1 → v1.0 completed.
- **Decision Engine v1.0 frozen for MVP contract.**
- Deterministic scoring remains a core architectural decision: the LLM does not calculate ranking.

### v1.0 scoring model
- `Decision Score = 65% Structural Fit + 35% Preference Fit`
- Preference priority weighting:
  - 1st priority: 50%
  - 2nd priority: 30%
  - 3rd priority: 20%
- Initial calibration benchmark:
  - 12 synthetic scenarios
  - Top-2 acceptance: 100%
  - MRR: 0.958
  - 11 automated tests passing at freeze time

These are development/calibration results, not real-world automotive validation.

### Important next evolution
The original v1 calibration was primarily car-oriented. The engine must now be extended cleanly to vehicle-type-aware scoring:

- `car` → Car Decision Model
- `motorcycle` → Motorcycle Decision Model
- `scooter` → Scooter Decision Model

Common pillars can be shared, but specialist metrics must differ.

Examples:
- Moto: seat height, wet weight, rider experience, passenger comfort, wind protection.
- Scooter: underseat storage, urban agility, parking ease, ring-road suitability.
- Auto: family fit, luggage, garage compatibility, TCO, highway/city fit.

## Dataset / Vehicle Knowledge Base
The dataset strategy has evolved from a simple mock JSON into a **functional coverage / Vehicle Knowledge Base** approach.

### Functional Coverage Dataset v1
A dedicated test dataset has been created to cover the main product branches:
- **30 vehicles total**
- **12 cars**
- **8 motorcycles**
- **10 scooters**

It includes scenarios for:
- Auto / Moto / Scooter
- Garage known / unknown dimensions / none
- Session reset
- Family use
- High mileage / usage fit
- Motorcycle beginner / touring / sport scenarios
- Scooter urban / storage / ring-road scenarios
- Security / theft-aware scenarios

The dataset is for functional development. Most technical / qualitative values are synthetic test data unless explicitly linked to a real external reference.

## Security & Risk / Theft Risk
A new information domain has been added to DriveWise: **Security & Risk**.

### Current model
Where public data is available, the Vehicle Knowledge Base can store:
- observed theft volume by model;
- data year;
- recovery rate where available;
- territorial context;
- source;
- data confidence.

### Methodological rule
**Absolute theft volume must not be presented as individual probability of theft.**

A widely circulated model may have more theft events simply because more examples are on the road.

Therefore:
- `observed_thefts` can be shown as an evidence-backed insight;
- a normalized `theft_risk_index` remains unset until a reliable exposure denominator is available by model / territory / period;
- Theft Risk should initially be an insight / optional preference metric, not a default hard constraint.

Future normalized concept:
`theft_rate = theft_events / exposed_vehicle_population`

Security & Risk is expected eventually to combine:
- theft risk;
- recalls;
- known issues;
- reliability;
- safety;
- insurance impact;
- maintenance / ownership risk.

## Backend
The repository already contains backend/data work and an API contract with vehicle and deterministic advisor capabilities.

Current verified architectural direction:

`Lovable → FastAPI REST API → Python Decision Engine → Vehicle Knowledge Base → ranked JSON → Decision Report`

The Decision Engine must **not** be reimplemented inside Lovable / JavaScript.

Before frontend integration is considered complete, backend status must be audited and the final Decision API contract frozen.

## NEXT — highest priority
### 1. Backend audit
Verify exactly what is currently implemented by Tommaso:
- available FastAPI endpoints;
- Swagger/OpenAPI;
- deployed/local URL;
- database state;
- current advisor/recommendation logic;
- whether the frozen Decision Engine v1.0 is actually imported or an independent scoring implementation exists.

### 2. Freeze final Decision API contract
Target conceptual endpoint:
`POST /api/v1/decision/analyze`

Request must support:
- decision session ID;
- vehicle type;
- budget;
- annual km;
- usage;
- priorities;
- garage status / dimensions when known;
- type-specific fields for car / motorcycle / scooter.

Response should include at minimum:
- decision ID;
- profile completeness;
- decision confidence;
- ranked vehicles;
- Decision Score;
- pillar scores;
- strengths;
- trade-offs;
- explainability;
- excluded vehicles / reasons;
- conditional report data.

### 3. First real vertical slice
`Lovable /app/start → POST decision API → Python Decision Engine → ranked response → Decision Report UI`

Success criteria:
- no hardcoded ranking;
- no mock Decision Score / Confidence;
- new analysis creates a clean session;
- three consecutive analyses (Auto, Moto, Scooter) produce independent profiles, rankings and reports;
- Garage Fit is rendered only when dimensions are known.

## After first vertical slice
1. Vehicle detail APIs / remove hardcoded vehicle page data.
2. Session persistence and Decision History.
3. Real user authentication.
4. Vehicle Knowledge Base ingestion / validation pipeline.
5. Replace synthetic values with validated / sourced production data.
6. Expand catalog beyond functional test set.
7. Human calibration exercise (30–50+ profiles).
8. Security & Risk enrichment.
9. Beta telemetry and feedback.
10. Activate selected personal-area modules.

## Near-term working principle
**Do not spend the next sprint redesigning the UI.**

The design and brand are sufficiently mature for the MVP. The priority is now to make the existing experience genuinely data-driven and connected to the deterministic Decision Engine.
