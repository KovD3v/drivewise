# Catalog v2: identity and evidence foundation

Implemented on 14 September 2026 following the
[architecture review](data-architecture-review.md): an executable contract and
additive evidence storage. The follow-up publication workflow is documented below.

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

The referenced synthetic HTML artifacts are now shipped under
`data/fixtures/catalog/artifacts`. This original contract-only checker neither
downloads files nor verifies their hashes, factual truth or source rights.
The new importer described below also verifies local artifact hashes. The v1 writer rejects
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

PR #12 stopped at validation/storage: the legacy identity constraint and required
model year still prevented publishing overlapping generations and unknown years.
The follow-up workflow below replaces that constraint after collision checks,
adapts readers and adds explicit staging/publication. It uses `catalog_v2_batches`
for tracking; the existing v1 `import_runs` contract remains unchanged.

Never automatically assign legacy `battery_kwh` or `horsepower` to a more specific
metric. The separate Decision Engine integration and Garage Fit issue remain as
recorded in the architecture review.

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

## Staging and publication (follow-up to PR #12)

Migration `0006_catalog_publication.sql` and `import_catalog_v2.py` complete the
local acquisition boundary. No crawler, external requests, LLM, or live database
migration is performed. The caller supplies a **reviewed, self-contained v2
bundle** and the original files under one artifact root.

Run from the repository root, using Python 3.11+ and the API dependencies:

```sh
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --check data/fixtures/catalog/catalog-v2.synthetic.json \
  --artifact-root data/fixtures/catalog/artifacts

# DATABASE_URL must point to the intended local PostgreSQL database.
uv run --frozen --project apps/api python apps/api/scripts/migrate.py
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --stage data/fixtures/catalog/catalog-v2.synthetic.json \
  --artifact-root data/fixtures/catalog/artifacts

# Replace BATCH_UUID with the UUID printed by --stage.
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --publish BATCH_UUID --artifact-root data/fixtures/catalog/artifacts
```

The shipped artifacts are explicitly synthetic and carry real SHA-256 hashes.
They exercise storage/API behavior and **never qualify for ranking**, even when a
fixture decision says `verified`. For real bundles, use the ignored
`data/private/catalog/` directory and complete the [source review](source-review.md).

`--check` is offline. `--stage` validates the contract and every artifact hash,
rejecting missing files and paths/symlinks outside the root, then stores the bundle
in `catalog_v2_batches`. It does not modify catalog identities or evidence tables.
Keep original files at their artifact paths: the database retains references,
not a separate file copy. `--publish` checks the files again and atomically writes
sources, identities, snapshots, observations, decisions and publication time.
Failure rolls back all publication writes; the staged batch remains available.

The canonical bundle hash makes staging idempotent. Republishing the same batch
returns `unchanged`. Other bundles may repeat unchanged evidence IDs, but an ID
with different content is rejected. Include complete predecessor chains and their
evidence in revision bundles. A stale bundle cannot replace a newer decision;
a competing successor is rejected by the database. Batch publishers serialize on
one transaction advisory lock. Existing sources retain their database metadata
and permissions: importing an older bundle cannot re-enable a revoked source.

### Identity migration and ownership

The new unique index covers case-insensitive make/model, vehicle type,
generation, phase, body style, model year and market, with `NULLS NOT DISTINCT`.
It is built **before** dropping the old constraint, so existing collisions abort
the migration. Years, body style, fuel and trim can remain unknown. No arbitrary
default variant is selected when the bundle does not name one.

New identities use stable canonical/variant keys. Existing v2 identities must
match exactly, including their identity evidence; the ingestion path cannot
silently rename, merge, split or reparent them. Such corrections require a
separately reviewed migration/mapping.

Adopting existing v1 records requires `--adopt-legacy` at publication and the
existing canonical/variant keys as the explicit mapping. Make, model, market,
model year and variant parent must agree, and all existing variants of each
adopted vehicle must be present. UUIDs and listing references are preserved.
The original rows are saved in `legacy_record`, with old provenance marked
historical. Legacy measurements are not promoted to verified facts or reinterpreted
as system power/usable battery capacity. Database triggers prevent the v1 writer
from updating v2-owned identities/specs. Back up the database before adoption;
reverting application code alone is not a supported data rollback.

### Current facts and consumers

`GET /vehicles/{vehicle_id}/facts` returns current decisions per variant, metric
and measurement context, including state, interval, evidence IDs, selected
source URL/excerpt/hash, policy and actor. `eligible` is separate from `status`:
identity evidence and all supporting observations must come from sourced,
permitted, licensed sources. Unknown, not-applicable and conflicted decisions
have no selected value. Unobserved metrics remain absent, not zero.

Current facts are SQL views over the immutable history. They select the revision
head **before** checking eligibility. Source revocation or a new negative decision
therefore removes a fact from calculations immediately, with no cache refresh or
fallback to an older verified value.

Compatibility reads project only exact, unambiguous values from one current
context covering the whole variant. Intervals, multiple contexts and configured
measurements stay available in the facts API but are not flattened. Consumption,
range and CO₂ require WLTP combined and a known non-PHEV powertrain; cargo requires
`method: VDA` and `seating_configuration: all_seats_up`. The legacy scalar mapping
covers seats, cargo, liquid/electric consumption, WLTP range and CO₂. Precise
power, battery, dimensions and other metrics remain in the facts API; ambiguous
legacy horsepower/battery fields remain null for v2 records.

Advisor and Model Analysis use the shared provenance and eligible scalar views.
Model Analysis now also excludes unreviewed, inactive, expired and stale offers,
and does not use an unreviewed vehicle base price. Missing age/identity inputs
produce no maintenance estimate. Recommendations persist decision/observation IDs
with their provenance and calculated evidence. Vehicle APIs, resolver and frontend
accept unknown years and trims; the API also exposes generation and powertrain
identity. The separate `decision_engine/` package is not integrated by this PR.

### Boundary for the scraping PR

Collectors must save immutable original files and emit this v2 bundle format.
Extraction/normalization, source onboarding, matching, conflict resolution and
agentic fact checking belong to the next PR. They may stage a bundle without
publishing it. Publication is not itself a factual verifier: it validates the
reviewed decisions and their structural/evidence requirements.

This pilot uses complete bundles, local artifact files and read-time SQL views.
Incremental cross-bundle references, identity correction tooling, large-scale
query optimization and remote artifact storage are separate changes when needed.

Publication verification (17 September 2026): **215 backend tests passed, none
skipped**, with Python 3.11.15 and a fresh disposable PostgreSQL 16 + pgvector.
Ruff passed. Frontend: **53 tests**, typecheck and production build passed;
React Doctor reported 100/100. The shipped fixture also passed the actual CLI
sequence `--check` → `--stage` → `--publish` → repeat (`unchanged`). No live Neon
database or real source was modified.
