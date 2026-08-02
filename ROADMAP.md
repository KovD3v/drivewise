# Drivewise Roadmap

## Purpose

This roadmap turns the product vision in `PRODUCT_BRIEF.MD` into a sequence of testable product stages.

Drivewise is being built as an adaptive vehicle companion, not a listing aggregator. It should help people make informed purchase decisions and remain useful throughout ownership, maintenance, upgrades, resale, and replacement.

The roadmap uses outcome gates instead of target dates. A stage is complete only when its user and trust outcomes are demonstrated; completing code alone is not sufficient.

## Product direction

Drivewise follows one continuous journey:

> Understand the person → identify the exact vehicle → support the purchase → establish ownership → monitor what matters → guide lifecycle decisions.

The current purchase-assistant MVP is the first stage of this journey. Its exact vehicle identity, offer matching, provenance, freshness, and uncertainty controls are foundations that later ownership and agent capabilities must reuse.

## Roadmap principles

### Guidance is the product

Listings, specifications, documents, and external sources are evidence. The product is the guidance that helps a person understand that evidence and act on it.

### Vehicle identity comes before automation

Recommendations, maintenance guidance, recalls, notifications, and upgrades must refer to the correct vehicle and variant. When identity or applicability is uncertain, Drivewise must say so and avoid unsupported conclusions.

### Adaptation must not hide material information

The advisor may change vocabulary, depth, examples, and interaction style according to the user. It must not hide safety information, uncertainty, provenance, legal constraints, or important trade-offs.

### Agents operate inside evidence and permission boundaries

Advisor and information-gathering agents must use authorized sources, retain attribution and dates, distinguish evidence from inference, and fail closed when permissions or applicability are unclear.

### Notifications must earn attention

Drivewise should notify users only when information is relevant to their exact vehicle or ownership decision, explain why it matters, and suggest an appropriate action. Notification volume is not a success metric.

### Each stage must validate a user outcome

Synthetic fixtures and automated tests prove system behavior, not market usefulness. Product stages require appropriate user validation before broader release claims are made.

## Stage 0 — Trustworthy purchase foundation

### Objective

Establish reliable vehicle identity, evidence handling, and deterministic purchase guidance before introducing broader agent autonomy.

### Included

- Canonical vehicle and exact-variant identity.
- Exact offer-to-variant pairing.
- Source permission and review state.
- Record- and metric-level provenance.
- Freshness and eligibility checks.
- Deterministic needs-based recommendations.
- Visible scores, strengths, compromises, assumptions, and missing data.
- Synthetic catalog readiness and automated verification.
- Authorization-gated, disabled-by-default marketplace ingestion infrastructure.

### Current foundation

- Synthetic catalog readiness is measurable with deterministic fixtures and
  read-only verification.
- The private-buyer beta contract is defined in `docs/product-beta.md`.
- Marketplace ingestion infrastructure is authorization-gated and offline-only;
  live use remains blocked pending written source authorization.

### Exit gate

- Exact vehicle, variant, offer, provenance, and freshness invariants pass automated tests.
- Unreviewed or unauthorized sources cannot affect recommendations.
- Catalog readiness can be reproduced for a pinned date.
- Live marketplace data is not presented or ranked without written authorization.

## Stage 1 — Complete the informed-purchase loop

### Objective

Move from producing ranked results to helping a user reach, understand, and act on a defensible purchase decision.

### Capabilities

- Reopen a recommendation run through a stable URL.
- Shortlist two or three exact offers.
- Compare benefits, compromises, evidence, freshness, and uncertainty.
- Preserve the selected offer, exact variant, and decision rationale together.
- Turn a result into a concrete next action:
  - inspect the offer;
  - compare an alternative;
  - open a purchase or inspection checklist;
  - revise the user's requirements.
- Make unsupported or insufficient-result states useful instead of forcing a recommendation.

### Next capabilities

- Make advisor runs retrievable and shareable through stable URLs.
- Add a 2–3 offer decision workspace.
- Add Italian ownership-tax estimates only after reviewed source data is
  supplied.

### Product validation

Run the private-buyer protocol defined in `docs/product-beta.md`. The stage succeeds when users can independently:

- reach a relevant shortlist;
- explain why the leading option fits;
- identify its main compromise or uncertainty;
- choose a concrete next action;
- avoid all trust-critical failures.

### Exit gate

- Retrievable advisor runs and the 2–3 offer decision workspace are complete
  and verified.
- The selected beta dataset supplies enough eligible offers for every tested scenario.
- At least four of five target users complete the core decision tasks without observer help.
- No incorrect offer-to-variant pairing, unauthorized evidence, unsupported provenance, or materially stale offer affects a result.

## Stage 2 — Establish the vehicle lifecycle spine

### Objective

Create continuity between purchase research and ownership so Drivewise does not end when a vehicle is bought.

### First design milestone

Define a user–vehicle relationship independently of any conversational or notification interface. It must connect a person to an exact known vehicle or explicitly uncertain identity.

The model should support lifecycle states such as:

- researched;
- compared;
- shortlisted;
- inspected;
- purchased;
- owned;
- maintained;
- modified;
- listed for sale;
- sold or replaced.

### Capabilities

- Convert a shortlisted or analyzed vehicle into an owned-vehicle profile.
- Retain canonical vehicle, exact variant, and user-supplied configuration details.
- Record lifecycle transitions with effective dates rather than overwriting history.
- Attach decisions, evidence, maintenance events, and later updates to the profile.
- Let users correct uncertain identity and configuration data.
- Define privacy, deletion, export, and access-control behavior before storing personal ownership data.

VIN or registration data must not be required for the first slice. If introduced later, it requires a separate privacy and security review.

### Product validation

Test one complete transition:

> Shortlisted vehicle → purchase decision → owned-vehicle profile.

Users should recognize the profile as their vehicle, understand which details are confirmed or uncertain, and see continuity with the original purchase evidence.

### Exit gate

- The user–vehicle conceptual model and lifecycle transitions are documented.
- One end-to-end purchase-to-ownership flow works for an exact variant.
- Lifecycle history is append-only and auditable.
- Privacy and deletion behavior are defined and tested.
- Notifications and conversational memory do not proceed until this identity layer is trustworthy.

## Stage 3 — Introduce the adaptive agent-based advisor

### Objective

Evolve the fixed recommendation and analysis flows into an advisor that adapts to the user while remaining grounded in deterministic evidence.

### Advisor contract

Define explicit boundaries for:

- stable user goals and constraints;
- current lifecycle stage;
- active vehicle or candidate vehicle;
- declared and inferred knowledge level, including confidence;
- conversation context and retention;
- permitted tools and actions;
- citation and provenance requirements;
- safety, legal, financial, and mechanical escalation;
- correction, deletion, and expiration of remembered information.

Conversation transcripts must not become the only source of durable user or vehicle truth. Confirmed profile facts, temporary conversation context, and system inferences should remain distinct.

### Initial vertical slices

Build and evaluate two deliberately different journeys over the same evidence layer:

1. A beginner asks a foundational question such as “What is a transmission?” and receives a clear explanation connected to a current purchase decision.
2. An experienced owner asks about an exhaust upgrade and receives compatibility, expected effects, cost, legality, warranty, emissions, safety, reversibility, and uncertainty guidance for an exact vehicle.

### Safety boundary

The agent may explain, compare, ask follow-up questions, and recommend next steps. It must not:

- invent compatibility or vehicle facts;
- make unsupported mechanical diagnoses;
- conceal uncertainty to appear helpful;
- autonomously purchase, book, contact, or modify anything;
- replace qualified mechanical or legal review when it is required.

### Exit gate

- Beginner and experienced users can obtain appropriately detailed answers from the same underlying evidence.
- The advisor retains useful context without carrying stale or incorrect facts forward.
- Every material factual claim is attributable or clearly labelled as an inference.
- Adaptation never removes safety information, provenance, uncertainty, or relevant trade-offs.
- Evaluation includes correction behavior and adversarial ambiguous-vehicle cases.

## Stage 4 — Vehicle-specific ownership intelligence

### Objective

Monitor authorized information sources and determine which developments matter to each owned vehicle.

### First pilot: official recalls

Begin with one narrow, authoritative, high-value signal rather than a general automotive news feed.

The recall pilot should support:

- authorized source registration;
- publication, effective, retrieval, and observation dates;
- exact-vehicle or variant applicability;
- geographic applicability;
- matching confidence and review state;
- conflict, correction, and supersession handling;
- severity and action guidance;
- duplicate prevention;
- an audit trail from source claim to user notification.

### Intelligence model

Ownership intelligence should be stored as evidence and events before it becomes notification copy. The model must distinguish:

- verified facts;
- estimates;
- source opinions or reports;
- Drivewise inferences;
- conflicting claims;
- stale or superseded information.

### Notification behavior

Each notification must answer:

- What changed?
- Why does it apply to this vehicle?
- How confident is the match?
- What is the source and date?
- What should the owner do next?
- Can it be dismissed, acknowledged, corrected, or revisited?

### Product validation

Measure precision, comprehension, and actionability—not volume or clicks alone.

### Exit gate

- A permitted official source produces normalized, attributable events.
- Relevant events can be matched to an exact owned vehicle with visible confidence.
- Duplicate, stale, corrected, and non-applicable events behave safely.
- Users understand why an update applies and what action is appropriate.
- No trust-critical false applicability occurs in the pilot.

## Stage 5 — Broaden ownership and lifecycle guidance

### Objective

Expand from recalls to the wider set of vehicle-specific decisions that make Drivewise useful throughout ownership.

### Candidate capability order

Expand one source and decision category at a time:

1. Manufacturer service and software notices.
2. Maintenance schedules and owner-recorded maintenance history.
3. Known mechanical issues with evidence quality and applicability controls.
4. Regulatory, emissions, tax, and access-zone changes.
5. Model-specific news and market-value developments.
6. Parts, accessories, and modification compatibility.
7. Resale preparation and replacement decisions.

Each category requires its own source authorization, evidence schema, applicability rules, safety review, and user validation. A successful recall pilot does not automatically validate upgrade or market-value advice.

### Exit gate

- Owners return after purchase for vehicle-specific value.
- Updates lead to useful, appropriate actions.
- Users can understand the evidence and uncertainty behind maintenance and upgrade guidance.
- Ownership decisions remain attached to the vehicle's evolving history.
- Continued use reflects trust and relevance rather than notification frequency.

## Parallel platform work

The following work supports multiple stages and should progress when required by the next validated slice.

### Evidence and provenance

- Preserve append-only observations where claim history matters.
- Support publication, retrieval, observation, and effective dates.
- Model conflicting and superseded claims.
- Distinguish fact, estimate, opinion, and inference.
- Keep source permission and review state fail-closed.

### Information acquisition

- Treat Firecrawl as one bounded acquisition tool, not the information architecture.
- Maintain an explicit authorized-source registry and allowlist.
- Separate acquisition, normalization, reconciliation, review, applicability, and notification.
- Do not let raw scraped output directly influence advice or ranking.
- Avoid broad crawling or discovery until source-specific pilots establish safe contracts.

### Evaluation

- Maintain deterministic tests for identity, pairing, freshness, provenance, and scoring.
- Add agent evaluations for grounding, adaptation, correction, and uncertainty.
- Add lifecycle tests for state transitions and history.
- Add notification tests for applicability, deduplication, supersession, and acknowledgement.
- Keep product outcome validation separate from automated verification.

### Product surface

As lifecycle capabilities become real, evolve the primary navigation around user journeys:

- Choose a vehicle.
- My vehicles.
- Updates.
- Ask Drivewise.

Vehicle, listing, document, ingestion, and provenance explorers may remain available as secondary evidence or operator surfaces. They should not define the primary consumer experience.

## Explicitly out of scope until separately approved

- Purchasing or selling vehicles on a user's behalf.
- Dealer lead generation or paid ranking placement.
- Autonomous booking, purchasing, contacting, repair, or modification actions.
- Unreviewed public scraping or data reuse without permission.
- Redis runtime infrastructure without a designed cache requirement.
- Broad public release before the relevant trust and data gates pass.
- Claims of mechanical, legal, financial, tax, safety, or investment certainty.
- Replacing qualified inspection, repair, installation, or legal professionals.

## Success framework

### Purchase success

- Users reach and understand a relevant shortlist.
- Users can explain the leading choice and its main compromise.
- Users recognize missing evidence and uncertainty.
- Users take an appropriate next action.
- Trust-critical purchase failures remain at zero.

### Lifecycle success

- A purchase decision can become a trustworthy owned-vehicle profile.
- Vehicle history remains understandable and correct over time.
- Owners return after purchase because the product remains useful.

### Advisor success

- Beginners understand without needing a second source to decode the answer.
- Experienced users can reach sufficient technical depth.
- The advisor remembers useful context and can be corrected.
- Evidence, uncertainty, and safety constraints remain visible at every depth.

### Notification success

- Relevant information reaches the correct vehicle owner.
- The user understands why it applies.
- The update leads to an appropriate action when action is needed.
- Incorrect, stale, duplicated, or unauthorized notifications do not reach users.

### Strategic success

- Guidance, not inventory volume, is the primary reason people use Drivewise.
- Marketplace access is one product input rather than the sole roadmap gate.
- The product remains useful from research through ownership and eventual replacement.
- Every expansion preserves exact identity, provenance, permission, and explicit uncertainty.

## Immediate priorities

The recommended near-term order is:

1. Complete retrievable advisor runs and the 2–3 offer decision workspace.
2. Continue the authorized marketplace pilot only within its existing written-permission gate.
3. Design the user–vehicle lifecycle model and the shortlisted-to-owned transition.
4. Define the adaptive advisor's memory, evidence, tool, and safety contract.
5. Design an official-recall ownership-intelligence pilot.
6. Reframe the consumer experience around choosing, owned vehicles, updates, and the advisor as those capabilities become real.

This order protects the credible purchase work already completed while making the next architectural commitment serve the complete Drivewise vision.
