CREATE TABLE IF NOT EXISTS vehicles (
  id uuid PRIMARY KEY,
  make text NOT NULL,
  model text NOT NULL,
  model_year integer NOT NULL CHECK (model_year BETWEEN 1980 AND 2100),
  body_style text NOT NULL,
  fuel_type text NOT NULL,
  market text NOT NULL DEFAULT 'IT',
  base_price_eur numeric(12, 2),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (make, model, model_year, market)
);

CREATE TABLE IF NOT EXISTS vehicle_specs (
  id uuid PRIMARY KEY,
  vehicle_id uuid NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
  trim text NOT NULL,
  drivetrain text,
  transmission text,
  engine text,
  horsepower integer CHECK (horsepower IS NULL OR horsepower > 0),
  battery_kwh numeric(6, 2) CHECK (battery_kwh IS NULL OR battery_kwh > 0),
  consumption_l_100km numeric(5, 2) CHECK (
    consumption_l_100km IS NULL OR consumption_l_100km > 0
  ),
  wltp_range_km integer CHECK (wltp_range_km IS NULL OR wltp_range_km > 0),
  co2_g_km integer CHECK (co2_g_km IS NULL OR co2_g_km >= 0),
  euro_emission_standard text,
  seats integer CHECK (seats IS NULL OR seats > 0),
  cargo_volume_liters numeric(7, 2) CHECK (
    cargo_volume_liters IS NULL OR cargo_volume_liters >= 0
  ),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (vehicle_id, trim)
);

CREATE TABLE IF NOT EXISTS sources (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  source_type text NOT NULL CHECK (
    source_type IN ('manual_seed', 'public_dataset', 'curated_internal')
  ),
  url text,
  license text,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS listings (
  id uuid PRIMARY KEY,
  vehicle_id uuid NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  listing_ref text NOT NULL,
  title text NOT NULL,
  price_eur numeric(12, 2) CHECK (price_eur IS NULL OR price_eur >= 0),
  mileage integer CHECK (mileage IS NULL OR mileage >= 0),
  condition text NOT NULL CHECK (condition IN ('new', 'used', 'certified')),
  location_region text,
  listed_at date,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, listing_ref)
);

CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  vehicle_id uuid REFERENCES vehicles(id) ON DELETE CASCADE,
  listing_id uuid REFERENCES listings(id) ON DELETE CASCADE,
  document_type text NOT NULL CHECK (
    document_type IN (
      'vehicle_profile',
      'listing_snapshot',
      'review_excerpt',
      'spec_sheet',
      'seed_note'
    )
  ),
  title text NOT NULL,
  content text NOT NULL,
  embedding vector(1536),
  embedding_model text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recommendation_runs (
  id uuid PRIMARY KEY,
  request_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'queued' CHECK (
    status IN ('queued', 'completed', 'failed')
  ),
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS recommendation_items (
  id uuid PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES recommendation_runs(id) ON DELETE CASCADE,
  vehicle_id uuid NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT,
  rank integer NOT NULL CHECK (rank > 0),
  score numeric(8, 4) CHECK (score IS NULL OR score >= 0),
  rationale text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, rank),
  UNIQUE (run_id, vehicle_id)
);

CREATE INDEX IF NOT EXISTS vehicle_specs_vehicle_id_idx
  ON vehicle_specs (vehicle_id);

CREATE INDEX IF NOT EXISTS listings_vehicle_id_idx
  ON listings (vehicle_id);

CREATE INDEX IF NOT EXISTS listings_source_id_idx
  ON listings (source_id);

CREATE INDEX IF NOT EXISTS documents_vehicle_id_idx
  ON documents (vehicle_id);

CREATE INDEX IF NOT EXISTS documents_source_id_idx
  ON documents (source_id);

CREATE INDEX IF NOT EXISTS recommendation_items_run_id_idx
  ON recommendation_items (run_id);

CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
  ON documents USING hnsw (embedding vector_cosine_ops)
  WHERE embedding IS NOT NULL;
