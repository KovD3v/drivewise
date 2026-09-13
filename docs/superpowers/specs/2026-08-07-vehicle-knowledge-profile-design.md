# Vehicle Knowledge Profile API Design

## Goal

Extend `GET /vehicles/{vehicle_id}` so the frontend can render a structured,
source-aware technical profile for every vehicle variant. The first increment
persists and returns one complete synthetic variant while keeping all existing
vehicle API fields backward compatible.

## Scope

The profile covers:

- variant identity and classification;
- dimensions, weight, seating, and cargo capacity;
- powertrain and battery data;
- transmission and drivetrain data;
- official performance;
- official homologation consumption, range, and emissions;
- scheduled maintenance;
- Euro NCAP assessments, ADAS, and safety equipment;
- technology and comfort equipment;
- photos, brochures, and manuals.

The following contextual or time-series domains are explicitly excluded from
this increment:

- insurance;
- vehicle tax;
- real-world consumption;
- reliability scores and defect probabilities;
- known defects and repair-cost estimates;
- recalls;
- parts, tyres, accessories, and aftermarket compatibility;
- valuations and depreciation;
- fuel-cost and total-cost calculations;
- recommendation or AI-generated interpretation.

No graph database, Firecrawl integration, Redis dependency, external data
source, or external media download is introduced.

## API Boundary

The existing route remains:

```text
GET /vehicles/{vehicle_id}
```

The response continues to use `VehicleDetail`, and each item in `specs`
retains its existing flat fields. New nested sections are additive, so the
current frontend and API consumers continue to work without changes.

The new sections on each specification are:

```json
{
  "identity": {
    "generation_name": "Second generation",
    "restyling_label": "2026 update",
    "category": "city_car",
    "doors": 5
  },
  "dimensions": {
    "length_mm": 3820,
    "width_mm": 1680,
    "height_mm": 1530,
    "wheelbase_mm": 2440,
    "curb_weight_kg": 1120,
    "gross_weight_kg": 1580,
    "payload_kg": 460,
    "seats": 5,
    "cargo_volume_liters": 280.0
  },
  "powertrain": {
    "engine_description": "1.0 turbo petrol",
    "engine_code": "SYN-T10",
    "displacement_cc": 999,
    "cylinders": 3,
    "horsepower": 100,
    "power_kw": 74.0,
    "torque_nm": 170,
    "fuel_type": "petrol",
    "battery_total_kwh": null,
    "battery_usable_kwh": null,
    "wltp_range_km": null
  },
  "transmission_details": {
    "transmission": "6-speed manual",
    "transmission_type": "manual",
    "gear_count": 6,
    "drivetrain": "fwd",
    "differential_type": "open"
  },
  "performance": {
    "acceleration_0_100_s": 10.8,
    "top_speed_kmh": 185,
    "braking_100_0_m": 36.5,
    "power_to_weight_kw_per_t": 66.07
  },
  "official_efficiency": {
    "homologation_cycle": "WLTP",
    "consumption_l_100km": 5.1,
    "energy_consumption_kwh_100km": null,
    "co2_g_km": 116,
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
```

All scalar section properties are nullable because source coverage can be
partial. Repeating collections are always arrays and default to `[]`.
`power_to_weight_kw_per_t` is derived at read time from `power_kw` and
`curb_weight_kg`; it is `null` when either input is absent or the weight is
zero.

## Repeating Resource Shapes

Each scheduled-maintenance item contains:

```json
{
  "id": "uuid",
  "operation_code": "engine-oil",
  "title": "Engine oil and filter",
  "interval_km": 15000,
  "interval_months": 12,
  "notes": "Whichever occurs first",
  "provenance": {}
}
```

Each safety rating contains the assessment system, assessment year, overall
stars, optional percentage scores for adult occupant, child occupant,
vulnerable road users, and safety assist, plus provenance.

Each feature contains a stable `feature_key`, display `name`, `availability`
(`standard` or `optional`), optional notes, and provenance. Features in the
`adas` category populate `safety.adas`; features in the `safety` category
populate `safety.equipment`; `technology` and `comfort` features populate
`technology_comfort`.

Each media item contains a stable `asset_key`, `asset_type` (`photo`,
`brochure`, or `manual`), title, HTTPS URL, optional MIME type, optional locale,
and provenance. The API returns external links only; it does not proxy or cache
the asset bytes.

The provenance object reuses the current source vocabulary and contains
`source_id`, `source_key`, `source_name`, `source_url`, optional
`source_license`, and `observed_at`. It does not expose content hashes for
these presentation resources.

## Persistence Model

Migration `0005_vehicle_knowledge_profile.sql` extends `vehicle_specs` with
nullable scalar facts:

- `generation_name`, `restyling_label`, `category`, `doors`;
- `length_mm`, `width_mm`, `height_mm`, `wheelbase_mm`;
- `curb_weight_kg`, `gross_weight_kg`, `payload_kg`;
- `engine_code`, `displacement_cc`, `cylinders`, `power_kw`, `torque_nm`;
- `battery_usable_kwh`;
- `transmission_type`, `gear_count`, `differential_type`;
- `acceleration_0_100_s`, `top_speed_kmh`, `braking_100_0_m`;
- `homologation_cycle`.

Existing columns remain authoritative for `body_style`, `fuel_type`,
`list_price_eur`, `drivetrain`, `transmission`, `engine`, `horsepower`,
`battery_kwh`, official consumption, WLTP range, CO2, emissions standard,
seats, and cargo volume. The endpoint composes old and new columns into the
nested sections without copying data into additional columns.

The migration adds four relational tables:

1. `vehicle_maintenance_items`, keyed by `spec_id` and `operation_code`.
2. `vehicle_safety_ratings`, keyed by `spec_id`, assessment system, and year.
3. `vehicle_features`, keyed by `spec_id` and `feature_key`, with a checked
   category of `adas`, `safety`, `technology`, or `comfort`.
4. `vehicle_media_assets`, keyed by `spec_id` and `asset_key`, with a checked
   type of `photo`, `brochure`, or `manual`.

Every child row references `sources`, stores the exact `source_url` plus a
timezone-aware `observed_at`, and is deleted when its specification is deleted.
Numeric columns receive non-negative or positive checks as appropriate.
Maintenance intervals require at least one of `interval_km` or
`interval_months`. Source and media URLs must begin with `https://`.

No JSONB blob is used for domain facts. Existing `metadata` remains unchanged
and is not read by this endpoint for the new profile.

## Curated Catalog Ingestion

The v1 curated catalog format is extended additively:

- new scalar fields are optional properties of a variant;
- `maintenance_schedule`, `safety_ratings`, `features`, and `media` are
  optional arrays on a variant;
- each child item carries `source_key`, `source_url`, and `observed_at`;
- validation rejects unknown source keys, duplicate stable keys within a
  variant, invalid category/type values, missing maintenance intervals, and
  non-HTTPS media URLs.

The importer upserts child rows transactionally with the parent variant. For a
variant present in a snapshot, each supplied child collection replaces that
collection for the variant. An omitted collection means “no update” so an
older catalog payload cannot erase data it does not know about. An explicit
empty collection removes the current child rows for that collection.

The synthetic catalog fixture enriches only
`it-acme-metro-2026-petrol`. All values and URLs remain clearly synthetic and
use the existing `drivewise-synthetic-catalog` source. Other variants remain
valid and return nullable scalar fields and empty child collections.

## Repository Data Flow

`VehiclesRepository.get_vehicle` continues to load the vehicle, variants, and
existing provenance. It adds bounded queries for maintenance items, safety
ratings, features, and media for all specification IDs belonging to the
requested vehicle. Results are grouped by `spec_id` in Python and attached to
the matching specification.

The endpoint does not execute one query per variant. The number of queries is
constant for a vehicle detail request, preventing an N+1 pattern.

Pydantic response models perform the final contract validation. A missing
vehicle still returns:

```json
{
  "detail": "Vehicle not found"
}
```

with HTTP `404`.

## Compatibility

- The route and path parameter do not change.
- Existing `VehicleSummary`, `VehicleDetail`, and flat `VehicleSpec` fields do
  not change type or meaning.
- New scalar fields are nullable.
- New collection fields default to empty arrays.
- Vehicle list, resolver, listing, advisor, and model-analysis contracts do not
  receive the new profile sections in this increment.
- No frontend code is changed; this work supplies a backend contract for the
  frontend owner to consume separately.

## Testing

The implementation follows test-driven development and covers:

1. Migration creation, constraints, foreign keys, indexes, and idempotency.
2. Catalog validation for valid profile data and each invalid boundary.
3. Catalog import persistence, idempotent re-import, update, omission, explicit
   clearing, and transactional rollback.
4. Repository grouping of all child resources without N+1 queries.
5. API serialization of a complete enriched variant.
6. API serialization of an unenriched variant with `null` and `[]` defaults.
7. Preservation of the existing flat fields and `404` response.
8. JSON Schema acceptance of the enriched synthetic fixture.

Focused backend tests, Ruff, the full backend test suite, and
`git diff --check` are required before completion is reported.

## Documentation

Implementation updates:

- `docs/api-contract.md` with the additive response contract;
- `docs/data-model.md` with the new columns and tables;
- `docs/catalog-import.md` with replacement-versus-omission semantics;
- `docs/catalog-v1.schema.json` with the additive input fields.
