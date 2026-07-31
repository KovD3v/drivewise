# Curated catalog imports

Drivewise catalog imports are reviewed JSON snapshots. They are separate from the
document-ingestion pipeline and never call a crawler or external service.

The v1 shape is defined in `docs/catalog-v1.schema.json`. A synthetic fixture is
available at `data/fixtures/catalog/catalog-v1.synthetic.json`.

Before changing a source to `ranking_permission: "permitted"`, complete the
human licence, access, metric-trust, and freshness review in
[`docs/source-review.md`](source-review.md).

Validate a snapshot without a database connection:

```bash
uv run --project apps/api python apps/api/scripts/import_catalog.py \
  --path data/fixtures/catalog/catalog-v1.synthetic.json \
  --check
```

Report how many imported listings are currently rankable, why others are
excluded, and which body-style or fuel-type coverage gaps remain:

```bash
uv run --project apps/api python apps/api/scripts/catalog_status.py
```

Use `--as-of <ISO8601>` to reproduce readiness at a specific observation time.
The status command opens a read-only database transaction and has no write mode.

Apply a validated snapshot transactionally:

```bash
uv run --project apps/api python apps/api/scripts/import_catalog.py \
  --path data/private/catalog/reviewed-italy.json \
  --write
```

`--check` and `--write` are mutually exclusive. A write validates all records and
cross-references before opening a transaction. Stable keys identify sources,
model-year-market vehicles, variants, and source listing references. Re-importing
an identical dataset is a no-op; changed records keep their database IDs. Missing
listings are never deactivated implicitly, so a snapshot must explicitly set
`is_active` to `false`.

Variant `fuel_type` and `body_style` values are restricted to the same checked-in
enums used by the Advisor and web form. Every source must explicitly declare a
`ranking_permission`: only `permitted` sources can contribute offers or metrics
to Advisor rankings; `not_permitted` and `manual_validation_only` records remain
available for review without becoming rankable.

Vehicle and variant records may provide `provenance_claims` when different
sources support different fields (for example, homologation metrics from a
public dataset and price/space fields from a reviewed local record). Each claim
lists its exact URL, observation time, and `supported_metrics`. The importer
validates that claims reference declared sources, do not claim null or unknown
fields, and do not assign one metric to more than one current source. When the
array is omitted, the record-level source is shorthand for all non-null fields.

Each successful observation replaces the record's complete current provenance
set; omitted claims become historical (`is_current = false`). Multiple claims
may remain current together. Imports with an `observed_at` older than the
stored current record (or an older listing observation) are rejected as a whole,
so stale snapshots cannot overwrite prices, active state, or catalog fields.
Recommendation evidence uses only current, permitted claims and intersects its
metric names with `metadata.supported_metrics`.

Real snapshots belong under `data/private/catalog/`, which is ignored. Only
synthetic fixtures may be committed unless redistribution permission is reviewed.
