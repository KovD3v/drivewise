ALTER TABLE vehicle_specs
  ADD COLUMN IF NOT EXISTS generation_name text,
  ADD COLUMN IF NOT EXISTS restyling_label text,
  ADD COLUMN IF NOT EXISTS category text,
  ADD COLUMN IF NOT EXISTS doors integer,
  ADD COLUMN IF NOT EXISTS length_mm integer,
  ADD COLUMN IF NOT EXISTS width_mm integer,
  ADD COLUMN IF NOT EXISTS height_mm integer,
  ADD COLUMN IF NOT EXISTS wheelbase_mm integer,
  ADD COLUMN IF NOT EXISTS curb_weight_kg integer,
  ADD COLUMN IF NOT EXISTS gross_weight_kg integer,
  ADD COLUMN IF NOT EXISTS payload_kg integer,
  ADD COLUMN IF NOT EXISTS engine_code text,
  ADD COLUMN IF NOT EXISTS displacement_cc integer,
  ADD COLUMN IF NOT EXISTS cylinders integer,
  ADD COLUMN IF NOT EXISTS power_kw numeric(7, 2),
  ADD COLUMN IF NOT EXISTS torque_nm integer,
  ADD COLUMN IF NOT EXISTS battery_usable_kwh numeric(7, 2),
  ADD COLUMN IF NOT EXISTS transmission_type text,
  ADD COLUMN IF NOT EXISTS gear_count integer,
  ADD COLUMN IF NOT EXISTS differential_type text,
  ADD COLUMN IF NOT EXISTS acceleration_0_100_s numeric(5, 2),
  ADD COLUMN IF NOT EXISTS top_speed_kmh integer,
  ADD COLUMN IF NOT EXISTS braking_100_0_m numeric(5, 2),
  ADD COLUMN IF NOT EXISTS homologation_cycle text;

ALTER TABLE vehicle_specs
  ADD CONSTRAINT vehicle_specs_doors_check CHECK (doors IS NULL OR doors > 0),
  ADD CONSTRAINT vehicle_specs_dimensions_check CHECK (
    (length_mm IS NULL OR length_mm > 0)
    AND (width_mm IS NULL OR width_mm > 0)
    AND (height_mm IS NULL OR height_mm > 0)
    AND (wheelbase_mm IS NULL OR wheelbase_mm > 0)
  ),
  ADD CONSTRAINT vehicle_specs_weights_check CHECK (
    (curb_weight_kg IS NULL OR curb_weight_kg > 0)
    AND (gross_weight_kg IS NULL OR gross_weight_kg > 0)
    AND (payload_kg IS NULL OR payload_kg > 0)
  ),
  ADD CONSTRAINT vehicle_specs_powertrain_profile_check CHECK (
    (displacement_cc IS NULL OR displacement_cc > 0)
    AND (cylinders IS NULL OR cylinders > 0)
    AND (power_kw IS NULL OR power_kw > 0)
    AND (torque_nm IS NULL OR torque_nm > 0)
    AND (battery_usable_kwh IS NULL OR battery_usable_kwh > 0)
  ),
  ADD CONSTRAINT vehicle_specs_transmission_profile_check CHECK (
    gear_count IS NULL OR gear_count > 0
  ),
  ADD CONSTRAINT vehicle_specs_performance_profile_check CHECK (
    (acceleration_0_100_s IS NULL OR acceleration_0_100_s > 0)
    AND (top_speed_kmh IS NULL OR top_speed_kmh > 0)
    AND (braking_100_0_m IS NULL OR braking_100_0_m > 0)
  );

CREATE TABLE IF NOT EXISTS vehicle_maintenance_items (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE CASCADE,
  operation_code text NOT NULL,
  title text NOT NULL,
  interval_km integer,
  interval_months integer,
  notes text,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicle_maintenance_source_https_check CHECK (
    source_url LIKE 'https://%'
  ),
  CONSTRAINT vehicle_maintenance_interval_check CHECK (
    (interval_km IS NOT NULL AND interval_km > 0)
    OR (interval_months IS NOT NULL AND interval_months > 0)
  ),
  UNIQUE (spec_id, operation_code)
);

CREATE TABLE IF NOT EXISTS vehicle_safety_ratings (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE CASCADE,
  assessment_system text NOT NULL,
  assessment_year integer NOT NULL CHECK (assessment_year BETWEEN 1990 AND 2100),
  overall_stars integer CHECK (overall_stars BETWEEN 0 AND 5),
  adult_occupant_percent integer CHECK (adult_occupant_percent BETWEEN 0 AND 100),
  child_occupant_percent integer CHECK (child_occupant_percent BETWEEN 0 AND 100),
  vulnerable_road_users_percent integer CHECK (vulnerable_road_users_percent BETWEEN 0 AND 100),
  safety_assist_percent integer CHECK (safety_assist_percent BETWEEN 0 AND 100),
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicle_safety_ratings_source_https_check CHECK (
    source_url LIKE 'https://%'
  ),
  UNIQUE (spec_id, assessment_system, assessment_year)
);

CREATE TABLE IF NOT EXISTS vehicle_features (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE CASCADE,
  feature_key text NOT NULL,
  category text NOT NULL,
  name text NOT NULL,
  availability text NOT NULL,
  notes text,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicle_features_source_https_check CHECK (
    source_url LIKE 'https://%'
  ),
  CONSTRAINT vehicle_features_category_check CHECK (
    category IN ('adas', 'safety', 'technology', 'comfort')
  ),
  CONSTRAINT vehicle_features_availability_check CHECK (
    availability IN ('standard', 'optional')
  ),
  UNIQUE (spec_id, feature_key)
);

CREATE TABLE IF NOT EXISTS vehicle_media_assets (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE CASCADE,
  asset_key text NOT NULL,
  asset_type text NOT NULL,
  title text NOT NULL,
  url text NOT NULL,
  mime_type text,
  locale text,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL,
  observed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicle_media_assets_type_check CHECK (
    asset_type IN ('photo', 'brochure', 'manual')
  ),
  CONSTRAINT vehicle_media_assets_source_https_check CHECK (
    source_url LIKE 'https://%'
  ),
  CONSTRAINT vehicle_media_assets_https_check CHECK (url LIKE 'https://%'),
  UNIQUE (spec_id, asset_key)
);

CREATE INDEX IF NOT EXISTS vehicle_maintenance_items_spec_id_idx
  ON vehicle_maintenance_items (spec_id);
CREATE INDEX IF NOT EXISTS vehicle_safety_ratings_spec_id_idx
  ON vehicle_safety_ratings (spec_id);
CREATE INDEX IF NOT EXISTS vehicle_features_spec_id_category_idx
  ON vehicle_features (spec_id, category);
CREATE INDEX IF NOT EXISTS vehicle_media_assets_spec_id_idx
  ON vehicle_media_assets (spec_id);
