# Guided Decision API contract v1

## Purpose

The Guided Decision API lets the frontend treat each interaction as an updated
decision state instead of an unstructured AI message. The wire contract is
camelCase and versioned as `guided-decision-v1`.

The backend keeps three responsibilities separate:

1. The interpreter extracts conservative profile updates from the conversation.
2. The decision engine computes completeness, confidence, missing information,
   and the highest-impact next question.
3. Advisor v3 performs deterministic eligibility, scoring, and ranking over
   reviewed exact vehicle/variant/offer pairs.

The current interpreter is a deliberately narrow Italian baseline with no
external model call. It recognizes high-signal facts and short contextual
answers. A future LLM-backed interpreter may replace this adapter, but it must
produce the same typed facts and must not own scoring, constraints, question
priority, or ranking.

## Endpoints

### `POST /guided-decisions`

Starts a persisted decision and processes its first message.

```json
{
  "message": "Cerco un SUV per la famiglia e vorrei spendere circa 35.000 €",
  "locale": "it-IT",
  "market": "IT"
}
```

`guided-decision-v1` supports only market `IT`.

### `POST /guided-decisions/{decisionId}/turns`

Processes another user message against the latest profile.

```json
{
  "message": "15.000",
  "expectedProfileVersion": 1
}
```

`expectedProfileVersion` is mandatory. A stale client receives `409`:

```json
{
  "detail": {
    "code": "profile_version_conflict",
    "currentProfileVersion": 2
  }
}
```

### `GET /guided-decisions/{decisionId}`

Returns the last complete response for reopening or resynchronizing the flow.

## Response

All three successful operations return the same shape:

```json
{
  "contractVersion": "guided-decision-v1",
  "decisionId": "60000000-0000-4000-8000-000000000001",
  "profileVersion": 1,
  "status": "active",
  "message": "Perfetto, ho aggiornato il profilo: categoria suv, uso principale family, budget circa 35.000 EUR. Quanti chilometri percorri ogni anno?",
  "decisionProfile": {
    "vehicleType": {
      "value": "car",
      "confidence": 0.99,
      "source": "inferred",
      "confirmed": false,
      "updatedAt": "2026-08-12T10:00:00Z"
    },
    "category": {
      "value": "suv",
      "confidence": 0.98,
      "source": "user",
      "confirmed": true,
      "updatedAt": "2026-08-12T10:00:00Z"
    },
    "budgetEur": {
      "value": 35000.0,
      "confidence": 0.98,
      "source": "user",
      "confirmed": true,
      "updatedAt": "2026-08-12T10:00:00Z"
    },
    "family": {
      "value": true,
      "confidence": 0.98,
      "source": "user",
      "confirmed": true,
      "updatedAt": "2026-08-12T10:00:00Z"
    },
    "primaryUse": {
      "value": "family",
      "confidence": 0.95,
      "source": "user",
      "confirmed": true,
      "updatedAt": "2026-08-12T10:00:00Z"
    },
    "annualKm": null,
    "condition": null,
    "preferredFuelType": null,
    "maxMileageKm": null,
    "priorities": null,
    "parking": null,
    "garage": {
      "usefulLengthMm": null,
      "usefulWidthMm": null,
      "usefulHeightMm": null,
      "doorWidthMm": null,
      "doorHeightMm": null
    }
  },
  "updatedFields": [
    "category",
    "vehicle_type",
    "budget_eur",
    "family",
    "primary_use"
  ],
  "profileCompletion": 0.5,
  "decisionConfidence": 0.51,
  "missingInformation": [
    {
      "key": "annual_km",
      "priority": 0.92,
      "reason": "La percorrenza annua incide sulla scelta dell'alimentazione e sulla stima dei costi di utilizzo.",
      "affects": ["running_cost", "efficiency_range"]
    }
  ],
  "nextQuestion": {
    "id": "annual_km",
    "type": "number",
    "label": "Quanti chilometri percorri ogni anno?",
    "reason": "La percorrenza annua incide sulla scelta dell'alimentazione e sulla stima dei costi di utilizzo.",
    "constraints": {
      "minimum": 1.0,
      "maximum": null,
      "unit": "km/year",
      "options": []
    }
  },
  "previewRanking": {
    "status": "ready",
    "scoringVersion": "advisor-v3.0",
    "blockingReasons": [],
    "assumptions": [],
    "groups": []
  },
  "garageCompatibility": [],
  "warnings": []
}
```

The numeric values in this example illustrate the shape. Consumers must not
hard-code them.

## Profile facts

Each profile fact contains at least:

- `value`: typed value used by deterministic logic;
- `confidence`: confidence in extraction or inference, from `0` to `1`;
- `source`: `user`, `inferred`, `imported`, or `system_default`;
- `confirmed`: whether the user supplied or explicitly confirmed the fact;
- `updatedAt`: last update time.

Direct user statements are `source=user` and `confirmed=true`. A value derived
from another fact is `source=inferred` and remains unconfirmed. A later direct
statement replaces the current value; prior values remain auditable in the
append-only turn snapshots.

## Completion, confidence, and next question

`profileCompletion` is the answered fraction of a versioned weighted field set.
Only garage fields become applicable when `parking.value` is `garage`.

`decisionConfidence` is an engine signal, not a calibrated probability and not
the user's self-reported confidence. V1 combines confirmed fact coverage with a
small signal from ranking readiness. It must be labelled accordingly in the UI.

`missingInformation[].priority` represents the v1 engine's estimated impact on
the decision. The highest applicable priority becomes `nextQuestion`; the LLM
does not choose it. Priorities are recalculated after every profile update, so
the flow is not a fixed questionnaire.

## Preview ranking

`previewRanking` is an object rather than a bare array so an empty result is not
ambiguous:

- `blocked`: `budget_eur` or `primary_use` is missing;
- `ready`: Advisor v3 returned at least one eligible exact offer;
- `insufficient_inventory`: the profile is rankable, but no eligible reviewed
  offer is available.

The preview reuses `advisor-v3.0` without persisting a formal recommendation
run. Its assumptions remain visible, including a default annual distance when
`annual_km` is still unknown.

## Garage compatibility

The profile stores:

- useful internal length, width, and height;
- door width and height.

Every value is stored in millimetres. A geometric check additionally requires
reviewed vehicle measurements with explicit semantics:

- overall length;
- body width for internal lateral clearance;
- height;
- width with mirrors folded for the entrance.

A generic or semantically ambiguous vehicle width is not sufficient. The check
returns `insufficient_data` until every required user and vehicle measurement is
available. This fail-closed behavior prevents a false compatibility claim.

When data is complete, `garage-fit-v1` returns `comfortable`, `tight`, or
`incompatible` together with raw margins. `comfortable` means only that the
versioned geometric margins pass; it does not prove door-opening clearance,
turning room, ramps, columns, obstacles, or ease of manoeuvring. The frontend
must preserve that limitation.

## Persistence and privacy boundary

`guided_decisions` stores the current profile and last response.
`guided_decision_turns` stores one append-only snapshot per profile version.
No VIN, registration number, contact detail, analytics event, or external model
payload is introduced by this contract.
