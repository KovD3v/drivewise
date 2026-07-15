# Drivewise API Contract

## Scope

This MVP API exposes vehicle data, listing data, ingested document data, read-only document search, and deterministic advisor recommendations from PostgreSQL/Neon through `DATABASE_URL`.

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

Returns one vehicle with linked specs.

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
    }
  ]
}
```

404 response:

```json
{
  "detail": "Vehicle not found"
}
```

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

Creates a deterministic recommendation run and returns up to 5 ranked items.

The endpoint persists:

- the request body in `recommendation_runs.request_payload`
- generated item ranks, scores, and rationales in `recommendation_items`

Each response item also includes transient `document_evidence` built from text-only document search using the recommended vehicle make/model. This evidence is not persisted in `recommendation_items` and does not change advisor scores or ranking.

It does not call an LLM, generate embeddings, run vector search, or ingest external data.

Request body:

```json
{
  "budget_min_eur": 10000,
  "budget_max_eur": 22000,
  "primary_use": "city",
  "preferred_fuel_type": "mild_hybrid_petrol",
  "preferred_body_style": "city_car",
  "max_mileage": 30000,
  "priorities": ["price", "consumption"]
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

Allowed `priorities` values:

- `price`
- `consumption`
- `reliability`
- `space`
- `safety`
- `range`

Example response:

```json
{
  "run_id": "50000000-0000-4000-8000-000000000001",
  "items": [
    {
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
      "best_listing": {
        "id": "30000000-0000-4000-8000-000000000001",
        "vehicle_id": "00000000-0000-4000-8000-000000000001",
        "source_id": "10000000-0000-4000-8000-000000000001",
        "listing_ref": "seed-fiat-panda-2024-it",
        "title": "Fiat Panda 1.0 FireFly Hybrid",
        "price_eur": 14200.0,
        "mileage": 6400,
        "condition": "used",
        "location_region": "Piemonte",
        "listed_at": "2026-01-15"
      },
      "score": 104.25,
      "rationale": "Price fits the requested budget. City-car body style fits urban use. Low consumption supports city use. Price priority rewards lower cost. Consumption priority used WLTP l/100km.",
      "evidence": {
        "price_eur": 14200.0,
        "base_price_eur": 15500.0,
        "budget_min_eur": 10000.0,
        "budget_max_eur": 22000.0,
        "within_budget": true,
        "mileage": 6400,
        "max_mileage": 30000,
        "consumption_l_100km": 5.0,
        "wltp_range_km": null,
        "co2_g_km": 113,
        "seats": 4,
        "cargo_volume_liters": 225.0,
        "body_style": "city_car",
        "fuel_type": "mild_hybrid_petrol",
        "missing_fields": []
      },
      "document_evidence": [
        {
          "document_id": "40000000-0000-4000-8000-000000000001",
          "title": "Synthetic profile: Fiat Panda",
          "document_type": "seed_note",
          "score": 12.05,
          "snippet": "Synthetic profile: Fiat Panda"
        }
      ]
    }
  ]
}
```

MVP scoring rules:

- penalizes prices outside the requested budget, but keeps candidates in the result set
- rewards lower prices within budget
- rewards low `consumption_l_100km` when `consumption` is prioritized
- rewards `cargo_volume_liters` and `seats` for `family`
- rewards city cars, compact hatchbacks, and low consumption for `city` and `new_driver`
- rewards `wltp_range_km` or low consumption for `highway`
- rewards matching `preferred_fuel_type` and `preferred_body_style`
- penalizes missing data without automatically excluding a vehicle
- returns at most 5 items sorted by score descending

Document evidence rules:

- uses `POST /search/documents` text-only semantics internally;
- searches by vehicle `make` and `model`;
- returns at most 3 evidence documents per recommendation item;
- does not affect score, rationale, ranking, or persistence.
