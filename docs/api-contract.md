# Drivewise API Contract

## Scope

This MVP API exposes vehicle data, vehicle input resolution, listing data, ingested document data, read-only document search, deterministic advisor recommendations, and deterministic model analysis from PostgreSQL/Neon through `DATABASE_URL`.

Not included:

- Firecrawl ingestion
- Real external embeddings generation
- Production hybrid/vector search
- Authentication

## Base URL

Local development:

```text
http://127.0.0.1:8000
```

## Health

### GET /health

Returns cheap process health. This endpoint does not touch PostgreSQL.

Example response:

```json
{
  "status": "ok",
  "service": "drivewise-api"
}
```

### GET /ready

Verifies database readiness with a lightweight `SELECT 1`.

Example response:

```json
{
  "status": "ready",
  "service": "drivewise-api",
  "database": "ok"
}
```

If `DATABASE_URL` is missing outside local development, still contains placeholder values, or the database is unreachable, this endpoint returns `503`.

## Filtering and Pagination

Filter semantics are intentionally simple:

- `make`, `model`, `location_region`, and document `q` are case-insensitive contains matches.
- `fuel_type`, `body_style`, `market`, and `document_type` are exact matches.
- `limit` is capped at `100`.
- `offset` is zero-based and defaults to `0`.

## Vehicles

### GET /vehicles

Returns a list of vehicle summaries.

Supported query filters:

- `make`, contains, case-insensitive
- `model`, contains, case-insensitive
- `fuel_type`, exact
- `body_style`, exact
- `market`, exact
- `max_price_eur`
- `limit`, default `50`, maximum `100`
- `offset`, default `0`

Example:

```text
GET /vehicles?make=fi&market=IT&max_price_eur=20000&limit=50&offset=0
```

Example response:

```json
[
  {
    "id": "00000000-0000-4000-8000-000000000001",
    "make": "Fiat",
    "model": "Panda",
    "model_year": 2024,
    "body_style": "city_car",
    "fuel_type": "mild_hybrid_petrol",
    "market": "IT",
    "base_price_eur": 15500.0
  }
]
```

### POST /vehicles/resolve

Deterministically resolves a free-text vehicle description against canonical
vehicle and specification records in one market. It does not create or update
database records.

Optional `model_year`, `fuel_type`, and `body_style` fields improve ranking;
they are scoring hints rather than strict filters. `market` scopes the candidate
set and defaults to `IT`. `limit` defaults to `5` and is capped at `10`.

Example request:

```json
{
  "query": "Fiat Panda 1.0 FireFly hybrid 2024",
  "market": "IT",
  "model_year": 2024,
  "fuel_type": "mild_hybrid_petrol",
  "body_style": "city_car",
  "limit": 5
}
```

Example response:

```json
{
  "query": "Fiat Panda 1.0 FireFly hybrid 2024",
  "normalized_query": "fiat panda 1 0 firefly hybrid 2024",
  "status": "matched",
  "matches": [
    {
      "confidence": 1.0,
      "match_level": "spec",
      "vehicle": {
        "id": "00000000-0000-4000-8000-000000000001",
        "make": "Fiat",
        "model": "Panda",
        "model_year": 2024,
        "body_style": "city_car",
        "fuel_type": "mild_hybrid_petrol",
        "market": "IT",
        "base_price_eur": 15500.0
      },
      "spec": {
        "id": "20000000-0000-4000-8000-000000000001",
        "trim": "1.0 FireFly Hybrid",
        "drivetrain": "fwd",
        "transmission": "6-speed manual",
        "engine": "1.0L mild-hybrid petrol",
        "horsepower": 70,
        "battery_kwh": null,
        "consumption_l_100km": 5.0,
        "wltp_range_km": null,
        "co2_g_km": 113,
        "euro_emission_standard": "Euro 6e",
        "seats": 4,
        "cargo_volume_liters": 225.0
      },
      "matched_fields": [
        "make",
        "model",
        "model_year",
        "trim",
        "fuel_type",
        "body_style"
      ],
      "warnings": []
    }
  ]
}
```

`status` is `matched` for one sufficiently strong leading candidate,
`ambiguous` when plausible candidates are too close, and `no_match` when no
candidate reaches the minimum confidence. `match_level` is `vehicle` or `spec`.

### GET /vehicles/{vehicle_id}

Returns one vehicle with linked specs. This is the only vehicle endpoint that
returns the additive, detail-only knowledge profile: `GET /vehicles`,
`POST /vehicles/resolve`, listing responses, and Advisor selected specs retain
their existing flat summary/spec contracts. Model-analysis request and response
contracts also remain flat. Consumers must not infer that a profile field absent
from those endpoints is missing data.

All profile scalar fields are nullable and are returned as `null` when the
catalog has no value. Profile collections are always returned: an unavailable
collection is `[]`, and `safety` is always an object whose `ratings`, `adas`,
and `equipment` members are arrays. `power_to_weight_kw_per_t` is derived from
`power_kw` and `curb_weight_kg` (and is `null` unless both are available).

The existing flat spec fields remain for compatibility. Each detailed spec
adds the following groups:

- `identity`: `generation_name`, `restyling_label`, `category`, `doors`
- `dimensions`: `length_mm`, `width_mm`, `height_mm`, `wheelbase_mm`,
  `curb_weight_kg`, `gross_weight_kg`, `payload_kg`, `seats`,
  `cargo_volume_liters`
- `powertrain`: `engine_description`, `engine_code`, `displacement_cc`,
  `cylinders`, `horsepower`, `power_kw`, `torque_nm`, `fuel_type`,
  `battery_total_kwh`, `battery_usable_kwh`, `wltp_range_km`
- `transmission_details`: `transmission`, `transmission_type`, `gear_count`,
  `drivetrain`, `differential_type`
- `performance`: `acceleration_0_100_s`, `top_speed_kmh`,
  `braking_100_0_m`, `power_to_weight_kw_per_t`
- `official_efficiency`: `homologation_cycle`, `consumption_l_100km`,
  `energy_consumption_kwh_100km`, `co2_g_km`, `euro_emission_standard`
- `maintenance_schedule`, `safety`, `technology_comfort`, and `media`

`maintenance_schedule` items contain `id`, `operation_code`, `title`,
`interval_km`, `interval_months`, `notes`, and `provenance`. Safety ratings
contain `id`, `assessment_system`, `assessment_year`, `overall_stars`,
`adult_occupant_percent`, `child_occupant_percent`,
`vulnerable_road_users_percent`, `safety_assist_percent`, and `provenance`.
Features in `safety.adas`, `safety.equipment`, and `technology_comfort` contain
`id`, `feature_key`, `category`, `name`, `availability`, `notes`, and
`provenance`; only `adas` and `safety` categories populate the two `safety`
arrays, while `technology` and `comfort` populate `technology_comfort`. Media
items contain `id`, `asset_key`, `asset_type`, `title`, `url`, `mime_type`,
`locale`, and `provenance`.

Vehicle and flat-spec `provenance` arrays use record-level claims with
`source_id`, `source_key`, `source_name`, `source_url`, `source_license`,
`observed_at`, `record_observed_at`, `content_hash`, `is_current`, and
`supported_metrics`. Each profile child has its own `provenance` object with
`source_id`, `source_key`, `source_name`, `source_url`, `source_license`, and
`observed_at`; this is the source that supplied that particular child record.

The profile deliberately excludes contextual or time-series domains: insurance,
vehicle tax, real-world consumption, reliability scores or defect probabilities,
known defects and repair-cost estimates, recalls, parts/tyres/accessories and
aftermarket compatibility, valuations and depreciation, fuel-cost and
total-cost calculations, and recommendation or AI-generated interpretation.
Those omissions are product scope, not an indication that a response was
partially populated. The endpoint also does not fetch external sources or media.

Example response:

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "make": "Fiat",
  "model": "Panda",
  "model_year": 2024,
  "body_style": "city_car",
  "fuel_type": "mild_hybrid_petrol",
  "market": "IT",
  "base_price_eur": 15500.0,
  "specs": [
    {
      "id": "20000000-0000-4000-8000-000000000001",
      "variant_key": null,
      "is_default": false,
      "trim": "1.0 FireFly Hybrid",
      "body_style": "city_car",
      "fuel_type": "mild_hybrid_petrol",
      "list_price_eur": 15500.0,
      "drivetrain": "fwd",
      "transmission": "6-speed manual",
      "engine": "1.0L mild-hybrid petrol",
      "horsepower": 70,
      "battery_kwh": null,
      "energy_consumption_kwh_100km": null,
      "consumption_l_100km": 5.0,
      "wltp_range_km": null,
      "co2_g_km": 113,
      "euro_emission_standard": "Euro 6e",
      "seats": 4,
      "cargo_volume_liters": 225.0,
      "provenance": [],
      "identity": {
        "generation_name": null,
        "restyling_label": null,
        "category": null,
        "doors": null
      },
      "dimensions": {
        "length_mm": null,
        "width_mm": null,
        "height_mm": null,
        "wheelbase_mm": null,
        "curb_weight_kg": null,
        "gross_weight_kg": null,
        "payload_kg": null,
        "seats": 4,
        "cargo_volume_liters": 225.0
      },
      "powertrain": {
        "engine_description": "1.0L mild-hybrid petrol",
        "engine_code": null,
        "displacement_cc": null,
        "cylinders": null,
        "horsepower": 70,
        "power_kw": null,
        "torque_nm": null,
        "fuel_type": "mild_hybrid_petrol",
        "battery_total_kwh": null,
        "battery_usable_kwh": null,
        "wltp_range_km": null
      },
      "transmission_details": {
        "transmission": "6-speed manual",
        "transmission_type": null,
        "gear_count": null,
        "drivetrain": "fwd",
        "differential_type": null
      },
      "performance": {
        "acceleration_0_100_s": null,
        "top_speed_kmh": null,
        "braking_100_0_m": null,
        "power_to_weight_kw_per_t": null
      },
      "official_efficiency": {
        "homologation_cycle": null,
        "consumption_l_100km": 5.0,
        "energy_consumption_kwh_100km": null,
        "co2_g_km": 113,
        "euro_emission_standard": "Euro 6e"
      },
      "maintenance_schedule": [],
      "safety": {
        "ratings": [],
        "adas": [],
        "equipment": []
      },
      "technology_comfort": [],
      "media": []
    }
  ],
  "provenance": []
}
```

404 response:

```json
{
  "detail": "Vehicle not found"
}
```

### POST /vehicles/resolve

Resolves a dirty vehicle query into ranked canonical vehicle/spec matches. The endpoint is read-only and uses deterministic string matching over `vehicles` plus `vehicle_specs`.

Request body:

```json
{
  "query": "fiat panda 1.0 firefly hybrid 2024",
  "market": "IT",
  "model_year": 2024,
  "fuel_type": "mild_hybrid_petrol",
  "body_style": "city_car",
  "limit": 5
}
```

Fields:

- `query`, required, trimmed, 2-160 characters
- `market`, default `IT`; this is a hard filter
- `model_year`, `fuel_type`, and `body_style`, optional scoring hints
- `limit`, default `5`, maximum `10`

Response:

```json
{
  "query": "fiat panda 1.0 firefly hybrid 2024",
  "normalized_query": "fiat panda 1 0 firefly hybrid 2024",
  "status": "matched",
  "matches": [
    {
      "confidence": 1.0,
      "match_level": "spec",
      "vehicle": {
        "id": "00000000-0000-4000-8000-000000000001",
        "make": "Fiat",
        "model": "Panda",
        "model_year": 2024,
        "body_style": "city_car",
        "fuel_type": "mild_hybrid_petrol",
        "market": "IT",
        "base_price_eur": 15500.0
      },
      "spec": {
        "id": "20000000-0000-4000-8000-000000000001",
        "trim": "1.0 FireFly Hybrid",
        "drivetrain": "fwd",
        "transmission": "6-speed manual",
        "engine": "1.0L mild-hybrid petrol",
        "horsepower": 70,
        "battery_kwh": null,
        "consumption_l_100km": 5.0,
        "wltp_range_km": null,
        "co2_g_km": 113,
        "euro_emission_standard": "Euro 6e",
        "seats": 4,
        "cargo_volume_liters": 225.0
      },
      "matched_fields": ["make", "model", "model_year", "trim"],
      "warnings": []
    }
  ]
}
```

Resolver status values:

- `matched`: the first result is strong and sufficiently separated from the next result
- `ambiguous`: at least one plausible result exists, but the top result is weak or too close to another candidate
- `no_match`: no candidate reaches the minimum confidence threshold

## Listings

### GET /listings

Returns listing rows with linked vehicle summaries.

Supported query filters:

- `vehicle_id`
- `make`, contains, case-insensitive
- `model`, contains, case-insensitive
- `max_price_eur`
- `max_mileage`
- `location_region`, contains, case-insensitive
- `limit`, default `50`, maximum `100`
- `offset`, default `0`

`mileage` is stored as kilometres for the current Italy/EU seed data.

Example:

```text
GET /listings?make=fi&max_price_eur=15000&location_region=mont&limit=50&offset=0
```

Example response:

```json
[
  {
    "id": "30000000-0000-4000-8000-000000000001",
    "vehicle_id": "00000000-0000-4000-8000-000000000001",
    "source_id": "10000000-0000-4000-8000-000000000001",
    "listing_ref": "seed-fiat-panda-2024-it",
    "title": "Fiat Panda 1.0 FireFly Hybrid",
    "price_eur": 14200.0,
    "mileage": 6400,
    "condition": "used",
    "location_region": "Piemonte",
    "listed_at": "2026-01-15",
    "vehicle": {
      "id": "00000000-0000-4000-8000-000000000001",
      "make": "Fiat",
      "model": "Panda",
      "model_year": 2024,
      "body_style": "city_car",
      "fuel_type": "mild_hybrid_petrol",
      "market": "IT",
      "base_price_eur": 15500.0
    }
  }
]
```

### GET /listings/{listing_id}

Returns one listing with its linked vehicle summary.

404 response:

```json
{
  "detail": "Listing not found"
}
```

## Documents

### GET /documents

Returns ingested documents. The response intentionally excludes `embedding` and `embedding_model`.

Supported query filters:

- `source_id`
- `vehicle_id`
- `listing_id`
- `document_type`, exact
- `q`, contains, case-insensitive text search on `title` or `content`
- `limit`, default `20`, maximum `100`
- `offset`, default `0`

Example:

```text
GET /documents?document_type=seed_note&q=fiat&limit=10&offset=0
```

Example response:

```json
[
  {
    "id": "40000000-0000-4000-8000-000000000001",
    "source_id": "10000000-0000-4000-8000-000000000001",
    "vehicle_id": "00000000-0000-4000-8000-000000000001",
    "listing_id": "30000000-0000-4000-8000-000000000001",
    "document_type": "seed_note",
    "title": "Synthetic profile: Fiat Panda",
    "content": "Synthetic seed note for a compact Italian city car with mild-hybrid petrol power, low running costs, and urban-friendly dimensions.",
    "metadata": {
      "synthetic": true,
      "market_context": "IT"
    },
    "created_at": "2026-01-15T00:00:00Z"
  }
]
```

### GET /documents/{document_id}

Returns one ingested document with full `content` and `metadata`. The response does not include `embedding`.

404 response:

```json
{
  "detail": "Document not found"
}
```

## Search

### POST /search/documents

Returns read-only search results over `documents`. The default mode is `text_only`
and keeps the original deterministic text scoring. The optional `vector_fake`
mode is explicit dev/test functionality that searches existing fake embeddings
with pgvector.

The endpoint does not expose `embedding` or `embedding_model`, does not write to
PostgreSQL, and does not call external providers. `vector_fake` generates only
the query embedding through the local deterministic `FakeEmbeddingProvider`.

Request body:

```json
{
  "query": "fiat panda",
  "document_type": "seed_note",
  "limit": 10,
  "include_content": false,
  "mode": "text_only"
}
```

Fields:

- `query`, required non-blank string.
- `document_type`, optional exact filter.
- `limit`, default `10`, maximum `50`.
- `include_content`, default `false`; when `true`, each item includes full stored `content`.
- `mode`, optional, either `text_only` or `vector_fake`, default `text_only`.

Response:

```json
{
  "query": "fiat panda",
  "mode": "text_only",
  "items": [
    {
      "id": "40000000-0000-4000-8000-000000000001",
      "title": "Synthetic profile: Fiat Panda",
      "document_type": "seed_note",
      "score": 12.05,
      "snippet": "Synthetic profile: Fiat Panda",
      "metadata": {
        "source_id": "10000000-0000-4000-8000-000000000001",
        "vehicle_id": "00000000-0000-4000-8000-000000000001",
        "listing_id": "30000000-0000-4000-8000-000000000001",
        "created_at": "2026-01-15T00:00:00+00:00"
      }
    }
  ]
}
```

`text_only` scoring:

- exact phrase match in `title`: strongest signal;
- exact phrase match in `content`: stronger than token-only content matches;
- token matches in `title`: stronger than token matches in `content`;
- newer documents can receive a small tie-breaking boost;
- no text match returns an empty `items` array.

`vector_fake` behavior:

- generates a query vector with `FakeEmbeddingProvider` and model `fake-embedding-1536`;
- searches only rows where `documents.embedding IS NOT NULL`;
- orders by pgvector cosine distance using `<=>`;
- returns score as cosine similarity, `1 - cosine_distance`, where higher is better;
- returns an empty `items` array when no documents have embeddings;
- never exposes stored vectors or the embedding model in the response.

## Advisor

### POST /advisor/recommendations

Creates a deterministic Advisor v2 run from reviewed, imported Italian catalog
offers. It does not call an LLM, search documents, generate embeddings, or
ingest external data.

The endpoint persists the normalized request, scoring version, energy
assumptions, exclusion counts, and completion status on the run. Each selected
item persists its exact listing/spec pair, new/used group, group rank, score,
version, and complete score breakdown.

Request body:

```json
{
  "budget_min_eur": 10000,
  "budget_max_eur": 22000,
  "primary_use": "city",
  "condition": "any",
  "annual_km": 10000,
  "preferred_fuel_type": "mild_hybrid_petrol",
  "preferred_body_style": "city_car",
  "max_mileage": 30000,
  "priorities": ["price", "efficiency_range"]
}
```

Required fields:

- `budget_max_eur`
- `primary_use`

Allowed `primary_use` values:

- `city`
- `highway`
- `family`
- `work`
- `new_driver`

`condition` is `any` by default and accepts `any`, `new`, or `used`.
`certified` offers are returned in the `used` group. When `annual_km` is
omitted, it defaults to 10,000 for city/new-driver, 14,000 for family, and
18,000 for highway/work.

Allowed `priorities` values:

- `price`
- `efficiency_range`
- `space`
- `running_cost`

Example response:

```json
{
  "run_id": "50000000-0000-4000-8000-000000000001",
  "scoring_version": "advisor-v2.0",
  "assumptions": [
    "Annual distance: 10000 km (default for primary_use=city); used only for the annual energy-cost estimate.",
    "The running_cost component covers energy only; maintenance, tax, insurance, depreciation, and financing are excluded.",
    "it-energy-2026-07-16-v1: MIMIT fuel-price means...",
    "it-energy-2026-07-16-v1: ARERA electricity reference..."
  ],
  "excluded_counts_by_reason": {"stale_offer": 2},
  "groups": [
    {
      "condition": "new",
      "items": [
        {
          "vehicle": {"id": "...", "model_family_key": "it-fiat-panda"},
          "selected_spec": {"id": "...", "variant_key": "..."},
          "offer": {"id": "...", "spec_id": "...", "price_eur": 17500},
          "score": 86.42,
          "component_scores": {
            "price_fit": 89,
            "use_case_fit": 100,
            "running_cost": 54.17,
            "space": 62.5,
            "efficiency_range": 75
          },
          "positive_factors": [],
          "tradeoffs": [],
          "evidence": {"annual_km": 10000},
          "provenance": [
            {
              "metric": "consumption_l_100km",
              "source_name": "Reviewed catalog source",
              "source_url": "https://example.test/specs/panda",
              "observed_at": "2026-07-15T00:00:00Z"
            }
          ]
        }
      ]
    }
  ]
}
```

Eligibility is strict. Offers must be Italian, active, unexpired, observed in
the last 30 days, attached to a completed reviewed import and an exact spec,
and backed by spec provenance. Price, model-family identity, body, fuel, seats,
cargo, and powertrain consumption evidence are required. Used/certified offers
also require mileage. PHEVs are excluded, as are highway EVs below 250 km WLTP.
`budget_min_eur`, the 110% maximum-budget tolerance, and used `max_mileage` are
hard constraints; fuel and body preferences are soft.

Base component weights are price 30, use case 25, running cost 20, space 15,
and efficiency/range 10. Each selected priority multiplies its component weight
by 1.5, then all weights are normalized to 100. Component formulas are fixed:

- price is 100 through 75% of budget, falls linearly to 70 at budget, then to 0 at 110%;
- use case is 60% body/use matrix, 20% fuel preference, and 20% body preference;
- running cost is linear from 100 at EUR 5/100 km to 0 at EUR 15/100 km;
- space is 40% seat sufficiency and 60% use-specific cargo band;
- liquid efficiency is linear from 100 at 4 L/100 km to 0 at 8;
- EV efficiency/range averages the 14-24 kWh/100 km and 150-500 km curves.

Positive factors require a component score of at least 80; tradeoffs require a
score below 70. Any soft budget overrun is always reported with exact euros and
percentage. Offers are ranked before keeping the best offer per
`model_family_key`; at most five are returned per group. Stable ties use score,
price, make, model, then listing ID.

### POST /advisor/model-analysis

Analyzes a model already chosen by the user. The endpoint accepts either a free-text `query` resolved through `POST /vehicles/resolve` semantics or a canonical `vehicle_id`. It is deterministic, read-only, and does not create recommendation runs.

Request body:

```json
{
  "query": "toyota yaris active hybrid 2021",
  "market": "IT",
  "asking_price_eur": 14500,
  "current_km": 62000,
  "usage_profile": ["city", "mixed"],
  "analysis_scope": ["price", "maintenance", "red_flags", "tco"]
}
```

Response:

```json
{
  "status": "completed",
  "resolved_vehicle": {
    "id": "00000000-0000-4000-8000-000000000001",
    "make": "Fiat",
    "model": "Panda",
    "model_year": 2024,
    "body_style": "city_car",
    "fuel_type": "mild_hybrid_petrol",
    "market": "IT",
    "base_price_eur": 15500.0
  },
  "resolved_spec": {
    "id": "20000000-0000-4000-8000-000000000001",
    "trim": "1.0 FireFly Hybrid",
    "drivetrain": "fwd",
    "transmission": "6-speed manual",
    "engine": "1.0L mild-hybrid petrol",
    "horsepower": 70,
    "battery_kwh": null,
    "consumption_l_100km": 5.0,
    "wltp_range_km": null,
    "co2_g_km": 113,
    "euro_emission_standard": "Euro 6e",
    "seats": 4,
    "cargo_volume_liters": 225.0
  },
  "verdict": "interesting_with_checks",
  "price_assessment": "in_range",
  "estimated_costs": {
    "market_reference_price_eur": 14200.0,
    "estimated_annual_maintenance_eur": 576.0,
    "estimated_monthly_energy_eur": 92.5,
    "estimated_depreciation_3y_eur": 4060.0,
    "notes": ["annual_km_assumption:12000"]
  },
  "red_flags": [],
  "checklist": ["verify_service_history"],
  "confidence": 0.86,
  "assumptions": ["No live market sources are used in Model Analysis V1."],
  "warnings": [],
  "missing_data": [],
  "next_actions": [
    "modify_parameters",
    "open_checklist",
    "compare_alternatives"
  ]
}
```

Flow status values follow the MVP result contract:

- `completed`: enough input was available for a deterministic result
- `needs_input`: no vehicle was resolved or required price/km inputs are missing
- `low_confidence`: analysis is possible but the resolver result is ambiguous or fragile
- `error`: reserved for future flow failures

Model analysis rules:

- uses resolver confidence when the request starts from a query
- requires at least one `analysis_scope` value
- returns only estimates selected by `analysis_scope`; `tco` includes the price reference, energy/fuel cost, maintenance, and depreciation estimates
- requires asking price only for price or red-flag analysis, and current kilometres only for maintenance or red-flag analysis
- returns `requested_spec_not_found` instead of silently substituting another trim when an explicit `spec_id` is unknown
- compares asking price against available listing prices, then base price fallback
- estimates maintenance, monthly energy/fuel cost, and 3-year depreciation with deterministic MVP assumptions
- emits rule-based red flags for above-reference asking price and high mileage for age
- returns assumptions, warnings, missing data, and next actions for frontend display
