# Catalog v2: identity and evidence foundation

Implemented on 14 September 2026 following the
[architecture review](data-architecture-review.md): an executable contract and
additive evidence storage. Publication into the live catalog is a separate step.

## Validate a bundle

```sh
.venv/bin/python apps/api/scripts/check_catalog_v2.py \
  --path data/fixtures/catalog/catalog-v2.synthetic.json
```

This command needs no database credentials or network access. It validates a
complete bundle with 3 vehicle identities, 5 variants, 2 snapshots, 7 observations
and 3 decisions. All fixture values are synthetic, including the decision labelled
`verified`. That label represents a review outcome inside the example, not
authoritative vehicle data. Source permission is `manual_validation_only`.

The referenced HTML paths are illustrative. Validation neither downloads files
nor verifies their hashes, factual truth or source rights. The v1 writer rejects
v2 payloads, preventing accidental publication through the existing import path.

## Contract

The executable authority is
[`catalog_v2.py`](../apps/api/app/ingestion/catalog_v2.py).
[`catalog-v2.schema.json`](catalog-v2.schema.json) is generated from its models.
The `x-metric-units` annotation documents canonical units. Cross-record and
semantic checks require the Python validator; JSON Schema alone is insufficient.

Regenerate after changing the contract:

```sh
PYTHONPATH=apps/api .venv/bin/python - <<'PY'
import json
from pathlib import Path
from app.ingestion.catalog_v2 import CatalogV2
Path('docs/catalog-v2.schema.json').write_text(
    json.dumps(CatalogV2.model_json_schema(), indent=2) + '\n'
)
PY
```

Identity keys are stable identifiers, not regenerated descriptions. Vehicle
uniqueness uses make/model (case insensitive), vehicle type, generation, phase,
body style, model year and market. Unknown attributes participate in this check;
duplicate unknown identities are not silently merged. Same-name trims can identify
different powertrains. Dates and model years can explicitly remain unknown.

Market validation checks uppercase two-letter form and excludes `EU`, `XX`, `ZZ`;
it is not a complete ISO country registry. A source's coverage can still be `EU`.
External references retain namespace and value on each variant and are not
globally unique commercial identifiers.

| Domain | Canonical metrics / units |
| --- | --- |
| Power | `engine_power_kw`, `system_power_kw`, `continuous_power_kw`: kW |
| Engine | `engine_displacement_cc`: cm3; `cylinders`: integer count |
| Battery | `battery_gross_kwh`, `battery_usable_kwh`: kWh |
| Consumption | `liquid_consumption_l_100km`: l/100km; `electric_consumption_kwh_100km`: kWh/100km |
| Range/emissions | `electric_range_km`: km; `co2_g_km`: g/km |
| Dimensions | `length_mm`, `body_width_mm`, `width_with_mirrors_mm`, `height_mm`: mm |
| Practicality | `seats`: integer count; `cargo_volume_liters`: l; `mass_kg`: kg |
| Charging | `ac_charge_power_kw`, `dc_peak_charge_power_kw`: kW |

An exact measurement uses equal `value_min` and `value_max`. Intervals stay
intervals. Original value/unit, source excerpt/locator and extractor version are
retained. No implicit conversion of CV/hp, gross/usable capacity, engine/system
power or WLTP/NEDC is performed; source normalizers are not implemented here.

Consumption, electric range and CO₂ require procedure and cycle. Unknown
procedures can be stored as observations but cannot be verified. PHEV verification
also requires battery operating condition. Cargo volume requires method and
seating configuration; mass requires its definition. Unknown qualifiers do not
prove equivalence: review must resolve material configuration differences.
Serialized measurement context is limited to 1800 UTF-8 bytes in both validation
and SQL so complete contexts fit the composite foreign-key indexes. Longer source
text belongs in the evidence excerpt, not in a context identifier.

An observation can identify a variant, retain candidate keys or remain unmatched.
Only resolved observations can support decisions. Definite market or
validity-period mismatches are rejected. An omitted metric has no observation and
is unknown; zero is not substituted for missing data.
Applicability is checked for decisions without observations as well, including
`unknown` and `not_applicable` states.

Decisions record `verified`, `unknown`, `not_applicable` or `conflicted`:

- `verified` selects an observation from its evidence list.
- `conflicted` retains competing observations and cannot select a winner.
- `unknown` and `not_applicable` explain missing values without inventing them.

Every supporting observation must share the decision's variant, metric and
context, and must have been acquired before the decision. Multiple corroborating
observations are allowed. Decisions are ordered oldest first in one linear chain
through `supersedes_id`. Neither validation nor SQL implements majority voting,
source independence detection, an agent or an automatic truth classifier.

## Storage and compatibility

[`0005_catalog_evidence.sql`](../apps/api/migrations/0005_catalog_evidence.sql)
adds nullable vehicle type/generation/phase and variant powertrain/validity
attributes. It does not infer them from existing labels. UUIDs, legacy values
and source permissions are preserved.

| New table | Responsibility |
| --- | --- |
| `source_snapshots` | Source, URL, dates, SHA-256, artifact reference and evidence kind. Identical bytes can be acquired again at a later time. |
| `spec_observations` | Original/normalized measurement, context, excerpt/locator, extractor version, resolved spec FK or candidate keys. |
| `fact_decisions` | State, selected observation, evidence IDs, reason/actor/policy/time and preceding decision. |

Update/delete triggers preserve history. Composite foreign keys bind selected
evidence and preceding decisions to the same fact; unique indexes prevent two
roots or competing successors. A trigger validates all evidence IDs, their scope
and chronology. SQL also rejects unknown metric names, wrong units, nonfinite
numbers, invalid intervals and missing core measurement qualifiers. Application
validation remains required for the complete contract, including candidate
references, detailed context and PHEV applicability.

The publication schema still has the legacy identity constraint and required
model year. Thus overlapping generations and unknown years are currently
validated in v2 bundles, **not imported into `vehicles`**. No v2 write CLI is
exposed. This avoids making v1 readers consume rows they cannot interpret.
The migration does not use `import_runs`, whose schema version remains 1.

Next: staging/import and publication with explicit identity mappings, compatible
API handling of missing years, then replacement of the legacy identity constraint
after collision checks. Never automatically assign legacy `battery_kwh` or
`horsepower` to a more specific metric. All consumers must respect source
eligibility and selected decisions before real v2 data is published. The separate
Decision Engine integration and Garage Fit issue remain as recorded in the review.

## Verification

Tests use disposable PostgreSQL 16 + pgvector, matching the existing CI database.
Point `TEST_DATABASE_URL` and `DATABASE_URL` only at a disposable database:

```sh
APP_ENV=test .venv/bin/python -m pytest apps/api -q
.venv/bin/ruff check apps/api
```

The evidence integration test checks fresh migration, a second migration run
without changes, and a 0004 → 0005 upgrade inside an isolated schema rolled back
at completion. It exercises preserved IDs/values, immutable revisions, invalid
evidence associations, fork rejection and every metric/unit pair.

Verified after review on 14 September 2026: **206 backend tests passed, none skipped**,
using Python **3.11.15**, frozen dependencies and PostgreSQL **16.15** with
pgvector; Ruff passed. Both the v2 validation
command and the existing v1 `--check` command passed. The disposable container
was removed after verification; no live Neon database was migrated.

The older import integration test uses `catalog-v1.import-test.synthetic.json`,
keeping its original transactional scenarios independent of the larger coverage
fixture. `catalog-v1.synthetic.json` remains the coverage suite's dataset.

The SQL uses the project's PostgreSQL 16 target;
[PostgreSQL's constraint documentation](https://www.postgresql.org/docs/16/ddl-constraints.html)
describes the foreign-key and uniqueness guarantees used here.
