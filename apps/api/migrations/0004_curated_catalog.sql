ALTER TABLE vehicles
  ADD COLUMN IF NOT EXISTS canonical_key text,
  ADD COLUMN IF NOT EXISTS model_family_key text;

UPDATE vehicles
SET canonical_key = lower(
      trim(
        both '-' FROM regexp_replace(
          concat_ws('-', market, make, model, model_year::text),
          '[^a-zA-Z0-9]+',
          '-',
          'g'
        )
      )
    ),
    model_family_key = lower(
      trim(
        both '-' FROM regexp_replace(
          concat_ws('-', market, make, model),
          '[^a-zA-Z0-9]+',
          '-',
          'g'
        )
      )
    )
WHERE canonical_key IS NULL OR model_family_key IS NULL;

ALTER TABLE vehicles
  ALTER COLUMN canonical_key SET NOT NULL,
  ALTER COLUMN model_family_key SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS vehicles_canonical_key_key
  ON vehicles (canonical_key);

CREATE INDEX IF NOT EXISTS vehicles_model_family_key_idx
  ON vehicles (model_family_key);

ALTER TABLE sources
  ADD COLUMN IF NOT EXISTS source_key text,
  ADD COLUMN IF NOT EXISTS market text,
  ADD COLUMN IF NOT EXISTS ranking_permission text NOT NULL
    DEFAULT 'not_permitted';

UPDATE sources
SET source_key = lower(
      trim(
        both '-' FROM regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g')
      )
    ),
    market = COALESCE(market, 'IT')
WHERE source_key IS NULL OR market IS NULL;

ALTER TABLE sources
  ALTER COLUMN source_key SET NOT NULL,
  ALTER COLUMN market SET NOT NULL,
  ALTER COLUMN market SET DEFAULT 'IT';

ALTER TABLE sources
  ADD CONSTRAINT sources_ranking_permission_check
    CHECK (
      ranking_permission IN (
        'permitted',
        'not_permitted',
        'manual_validation_only'
      )
    );

CREATE UNIQUE INDEX IF NOT EXISTS sources_source_key_key
  ON sources (source_key);

ALTER TABLE vehicle_specs
  ADD COLUMN IF NOT EXISTS variant_key text,
  ADD COLUMN IF NOT EXISTS is_default boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS body_style text,
  ADD COLUMN IF NOT EXISTS fuel_type text,
  ADD COLUMN IF NOT EXISTS list_price_eur numeric(12, 2),
  ADD COLUMN IF NOT EXISTS energy_consumption_kwh_100km numeric(6, 2);

UPDATE vehicle_specs AS spec
SET variant_key = concat(
      vehicle.canonical_key,
      '-',
      lower(
        trim(
          both '-' FROM regexp_replace(spec.trim, '[^a-zA-Z0-9]+', '-', 'g')
        )
      )
    ),
    body_style = COALESCE(spec.body_style, vehicle.body_style),
    fuel_type = COALESCE(spec.fuel_type, vehicle.fuel_type),
    list_price_eur = COALESCE(spec.list_price_eur, vehicle.base_price_eur)
FROM vehicles AS vehicle
WHERE vehicle.id = spec.vehicle_id
  AND (
    spec.variant_key IS NULL
    OR spec.body_style IS NULL
    OR spec.fuel_type IS NULL
    OR spec.list_price_eur IS NULL
  );

WITH ranked_specs AS (
  SELECT
    id,
    row_number() OVER (PARTITION BY vehicle_id ORDER BY trim, id) AS position
  FROM vehicle_specs
)
UPDATE vehicle_specs AS spec
SET is_default = ranked_specs.position = 1
FROM ranked_specs
WHERE ranked_specs.id = spec.id;

ALTER TABLE vehicle_specs
  ALTER COLUMN variant_key SET NOT NULL,
  ALTER COLUMN body_style SET NOT NULL,
  ALTER COLUMN fuel_type SET NOT NULL;

ALTER TABLE vehicle_specs
  ADD CONSTRAINT vehicle_specs_list_price_eur_check
    CHECK (list_price_eur IS NULL OR list_price_eur >= 0),
  ADD CONSTRAINT vehicle_specs_energy_consumption_check
    CHECK (
      energy_consumption_kwh_100km IS NULL
      OR energy_consumption_kwh_100km > 0
    );

ALTER TABLE vehicle_specs
  DROP CONSTRAINT IF EXISTS vehicle_specs_vehicle_id_trim_key;

CREATE UNIQUE INDEX IF NOT EXISTS vehicle_specs_variant_key_key
  ON vehicle_specs (variant_key);

ALTER TABLE vehicle_specs
  ADD CONSTRAINT vehicle_specs_id_vehicle_id_key UNIQUE (id, vehicle_id);

CREATE UNIQUE INDEX IF NOT EXISTS vehicle_specs_one_default_per_vehicle_idx
  ON vehicle_specs (vehicle_id)
  WHERE is_default;

CREATE TABLE IF NOT EXISTS import_runs (
  id uuid PRIMARY KEY,
  schema_version integer NOT NULL CHECK (schema_version = 1),
  dataset_hash text NOT NULL,
  file_name text NOT NULL,
  status text NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
  record_counts jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_message text,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE INDEX IF NOT EXISTS import_runs_dataset_hash_idx
  ON import_runs (dataset_hash, status);

CREATE UNIQUE INDEX IF NOT EXISTS import_runs_completed_dataset_hash_key
  ON import_runs (dataset_hash)
  WHERE status = 'completed';

ALTER TABLE listings
  ADD COLUMN IF NOT EXISTS spec_id uuid REFERENCES vehicle_specs(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS source_url text,
  ADD COLUMN IF NOT EXISTS first_seen_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_seen_at timestamptz,
  ADD COLUMN IF NOT EXISTS valid_until timestamptz,
  ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS content_hash text,
  ADD COLUMN IF NOT EXISTS import_run_id uuid REFERENCES import_runs(id) ON DELETE SET NULL;

ALTER TABLE listings
  ADD CONSTRAINT listings_spec_vehicle_match_fkey
    FOREIGN KEY (spec_id, vehicle_id)
    REFERENCES vehicle_specs (id, vehicle_id)
    ON DELETE RESTRICT;

ALTER TABLE listings
  ADD CONSTRAINT listings_id_vehicle_id_spec_id_key
    UNIQUE (id, vehicle_id, spec_id);

WITH single_specs AS (
  SELECT vehicle_id, min(id::text)::uuid AS spec_id
  FROM vehicle_specs
  GROUP BY vehicle_id
  HAVING count(*) = 1
)
UPDATE listings AS listing
SET spec_id = single_specs.spec_id
FROM single_specs
WHERE listing.vehicle_id = single_specs.vehicle_id
  AND listing.spec_id IS NULL;

UPDATE listings AS listing
SET source_url = COALESCE(listing.source_url, source.url),
    first_seen_at = COALESCE(
      listing.first_seen_at,
      listing.listed_at::timestamp AT TIME ZONE 'Europe/Rome',
      listing.created_at
    ),
    last_seen_at = COALESCE(
      listing.last_seen_at,
      listing.listed_at::timestamp AT TIME ZONE 'Europe/Rome',
      listing.updated_at,
      listing.created_at
    ),
    content_hash = COALESCE(
      listing.content_hash,
      md5(
        concat_ws(
          '|',
          listing.source_id::text,
          listing.listing_ref,
          listing.vehicle_id::text,
          listing.price_eur::text,
          listing.mileage::text,
          listing.condition,
          listing.listed_at::text
        )
      )
    )
FROM sources AS source
WHERE source.id = listing.source_id;

ALTER TABLE listings
  ALTER COLUMN first_seen_at SET NOT NULL,
  ALTER COLUMN last_seen_at SET NOT NULL,
  ALTER COLUMN content_hash SET NOT NULL,
  ADD CONSTRAINT listings_seen_order_check
    CHECK (last_seen_at >= first_seen_at),
  ADD CONSTRAINT listings_valid_until_check
    CHECK (valid_until IS NULL OR valid_until >= first_seen_at);

CREATE INDEX IF NOT EXISTS listings_spec_id_idx
  ON listings (spec_id);

CREATE INDEX IF NOT EXISTS listings_active_freshness_idx
  ON listings (is_active, last_seen_at DESC);

CREATE TABLE IF NOT EXISTS vehicle_provenance (
  id uuid PRIMARY KEY,
  vehicle_id uuid NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  record_observed_at timestamptz NOT NULL,
  content_hash text NOT NULL,
  import_run_id uuid REFERENCES import_runs(id) ON DELETE SET NULL,
  is_current boolean NOT NULL DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (vehicle_id, source_id)
);

CREATE TABLE IF NOT EXISTS vehicle_spec_provenance (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE CASCADE,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  record_observed_at timestamptz NOT NULL,
  content_hash text NOT NULL,
  import_run_id uuid REFERENCES import_runs(id) ON DELETE SET NULL,
  is_current boolean NOT NULL DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (spec_id, source_id)
);

CREATE INDEX IF NOT EXISTS vehicle_provenance_source_id_idx
  ON vehicle_provenance (source_id);

CREATE INDEX IF NOT EXISTS vehicle_spec_provenance_source_id_idx
  ON vehicle_spec_provenance (source_id);

CREATE INDEX IF NOT EXISTS vehicle_provenance_current_idx
  ON vehicle_provenance (vehicle_id, is_current);

CREATE INDEX IF NOT EXISTS vehicle_spec_provenance_current_idx
  ON vehicle_spec_provenance (spec_id, is_current);

ALTER TABLE recommendation_items
  ADD COLUMN IF NOT EXISTS listing_id uuid REFERENCES listings(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS spec_id uuid REFERENCES vehicle_specs(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS condition_group text NOT NULL DEFAULT 'legacy',
  ADD COLUMN IF NOT EXISTS scoring_version text,
  ADD COLUMN IF NOT EXISTS score_breakdown jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE recommendation_items
  ADD CONSTRAINT recommendation_items_listing_identity_fkey
    FOREIGN KEY (listing_id, vehicle_id, spec_id)
    REFERENCES listings (id, vehicle_id, spec_id)
    ON DELETE RESTRICT;

ALTER TABLE recommendation_items
  ADD CONSTRAINT recommendation_items_condition_group_check
    CHECK (condition_group IN ('new', 'used', 'legacy'));

ALTER TABLE recommendation_items
  DROP CONSTRAINT IF EXISTS recommendation_items_run_id_vehicle_id_key,
  DROP CONSTRAINT IF EXISTS recommendation_items_run_id_rank_key;

CREATE UNIQUE INDEX IF NOT EXISTS recommendation_items_run_group_vehicle_key
  ON recommendation_items (run_id, condition_group, vehicle_id);

CREATE UNIQUE INDEX IF NOT EXISTS recommendation_items_run_group_rank_key
  ON recommendation_items (run_id, condition_group, rank);

ALTER TABLE recommendation_runs
  ADD COLUMN IF NOT EXISTS scoring_version text,
  ADD COLUMN IF NOT EXISTS assumptions jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS exclusion_counts jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS recommendation_items_listing_id_idx
  ON recommendation_items (listing_id);

CREATE INDEX IF NOT EXISTS recommendation_items_spec_id_idx
  ON recommendation_items (spec_id);
