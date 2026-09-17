-- Evidence storage is additive. No legacy facts are promoted or reinterpreted.
-- The legacy identity constraint remains until the publication/backfill rollout.
ALTER TABLE vehicles
  ADD COLUMN vehicle_type text CHECK (
    vehicle_type IN ('car', 'motorcycle', 'scooter')
  ),
  ADD COLUMN generation_key text CHECK (length(trim(generation_key)) > 0),
  ADD COLUMN phase_key text CHECK (length(trim(phase_key)) > 0);

ALTER TABLE vehicle_specs
  ADD COLUMN powertrain_type text CHECK (
    powertrain_type IN ('ICE', 'MHEV', 'HEV', 'PHEV', 'BEV')
  ),
  ADD COLUMN valid_from date,
  ADD COLUMN valid_to date,
  ADD CONSTRAINT vehicle_specs_validity_check CHECK (
    valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from
  );

CREATE TABLE source_snapshots (
  id uuid PRIMARY KEY,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_url text NOT NULL CHECK (source_url ~ '^https?://[^/]+'),
  retrieved_at timestamptz NOT NULL,
  published_at timestamptz,
  content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
  artifact_path text NOT NULL CHECK (
    length(trim(artifact_path)) > 0
    AND artifact_path !~ '(^/|(^|/)\.\.(/|$)|\\)'
  ),
  media_type text NOT NULL CHECK (length(trim(media_type)) > 0),
  evidence_kind text NOT NULL CHECK (
    evidence_kind IN ('sourced', 'synthetic', 'legacy')
  ),
  CHECK (published_at IS NULL OR published_at <= retrieved_at),
  UNIQUE (source_id, source_url, retrieved_at, content_sha256)
);

CREATE INDEX source_snapshots_content_idx ON source_snapshots (content_sha256);

CREATE DOMAIN catalog_metric AS text CHECK (VALUE IN (
  'engine_power_kw', 'system_power_kw', 'continuous_power_kw',
  'engine_displacement_cc', 'cylinders', 'battery_gross_kwh',
  'battery_usable_kwh', 'liquid_consumption_l_100km',
  'electric_consumption_kwh_100km', 'electric_range_km', 'co2_g_km',
  'length_mm', 'body_width_mm', 'width_with_mirrors_mm', 'height_mm',
  'seats', 'cargo_volume_liters', 'mass_kg', 'ac_charge_power_kw',
  'dc_peak_charge_power_kw'
));

CREATE TABLE spec_observations (
  id uuid PRIMARY KEY,
  snapshot_id uuid NOT NULL REFERENCES source_snapshots(id) ON DELETE RESTRICT,
  spec_id uuid REFERENCES vehicle_specs(id) ON DELETE RESTRICT,
  candidate_variant_keys jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (
    jsonb_typeof(candidate_variant_keys) = 'array'
  ),
  metric catalog_metric NOT NULL,
  raw_value text NOT NULL CHECK (length(trim(raw_value)) > 0),
  raw_unit text,
  value_min numeric NOT NULL,
  value_max numeric NOT NULL,
  unit text NOT NULL,
  context jsonb NOT NULL CHECK (
    jsonb_typeof(context) = 'object'
    AND octet_length(context::text) <= 1800
    AND COALESCE(context->>'market' ~ '^[A-Z]{2}$', false)
    AND context->>'market' NOT IN ('EU', 'ZZ', 'XX')
  ),
  evidence_excerpt text NOT NULL CHECK (length(trim(evidence_excerpt)) > 0),
  evidence_locator text NOT NULL CHECK (length(trim(evidence_locator)) > 0),
  extractor_version text NOT NULL CHECK (length(trim(extractor_version)) > 0),
  CHECK (spec_id IS NULL OR candidate_variant_keys = '[]'::jsonb),
  CHECK (value_min NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)),
  CHECK (value_max NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)),
  CHECK (value_max >= value_min),
  CHECK (value_min > 0 OR (value_min = 0 AND metric IN ('co2_g_km', 'cargo_volume_liters'))),
  CHECK (metric NOT IN ('seats', 'cylinders') OR (
    value_min = trunc(value_min) AND value_max = trunc(value_max)
  )),
  CHECK (metric NOT IN (
    'liquid_consumption_l_100km', 'electric_consumption_kwh_100km',
    'electric_range_km', 'co2_g_km'
  ) OR COALESCE(
    context->>'procedure' IN ('WLTP', 'NEDC', 'declared', 'measured', 'unknown')
    AND context->>'cycle' IN ('combined', 'urban', 'highway', 'weighted_combined', 'unknown'),
    false
  )),
  CHECK (metric NOT IN ('cargo_volume_liters', 'mass_kg')
    OR nullif(trim(context->>'method'), '') IS NOT NULL),
  CHECK (metric <> 'cargo_volume_liters'
    OR nullif(trim(context->>'seating_configuration'), '') IS NOT NULL),
  CHECK (unit = CASE
    WHEN metric IN ('engine_power_kw', 'system_power_kw', 'continuous_power_kw',
                    'ac_charge_power_kw', 'dc_peak_charge_power_kw') THEN 'kW'
    WHEN metric IN ('battery_gross_kwh', 'battery_usable_kwh') THEN 'kWh'
    WHEN metric IN ('length_mm', 'body_width_mm', 'width_with_mirrors_mm', 'height_mm') THEN 'mm'
    WHEN metric IN ('seats', 'cylinders') THEN 'count'
    WHEN metric = 'engine_displacement_cc' THEN 'cm3'
    WHEN metric = 'liquid_consumption_l_100km' THEN 'l/100km'
    WHEN metric = 'electric_consumption_kwh_100km' THEN 'kWh/100km'
    WHEN metric = 'electric_range_km' THEN 'km'
    WHEN metric = 'co2_g_km' THEN 'g/km'
    WHEN metric = 'cargo_volume_liters' THEN 'l'
    WHEN metric = 'mass_kg' THEN 'kg'
  END),
  UNIQUE (id, spec_id, metric, context)
);

CREATE INDEX spec_observations_snapshot_idx ON spec_observations (snapshot_id);
CREATE INDEX spec_observations_fact_idx ON spec_observations (spec_id, metric);

CREATE TABLE fact_decisions (
  id uuid PRIMARY KEY,
  spec_id uuid NOT NULL REFERENCES vehicle_specs(id) ON DELETE RESTRICT,
  metric catalog_metric NOT NULL,
  context jsonb NOT NULL CHECK (
    jsonb_typeof(context) = 'object'
    AND octet_length(context::text) <= 1800
    AND COALESCE(context->>'market' ~ '^[A-Z]{2}$', false)
    AND context->>'market' NOT IN ('EU', 'ZZ', 'XX')
  ),
  status text NOT NULL CHECK (
    status IN ('verified', 'unknown', 'not_applicable', 'conflicted')
  ),
  selected_observation_id uuid,
  evidence_ids uuid[] NOT NULL DEFAULT '{}',
  supersedes_id uuid UNIQUE,
  reason text NOT NULL CHECK (length(trim(reason)) > 0),
  actor_kind text NOT NULL CHECK (actor_kind IN ('human', 'rule', 'agent')),
  actor_id text NOT NULL CHECK (length(trim(actor_id)) > 0),
  policy_version text NOT NULL CHECK (length(trim(policy_version)) > 0),
  decided_at timestamptz NOT NULL,
  CHECK ((status = 'verified') = (selected_observation_id IS NOT NULL)),
  CHECK (selected_observation_id IS NULL OR selected_observation_id = ANY(evidence_ids)),
  CHECK (status <> 'conflicted' OR cardinality(evidence_ids) >= 2),
  CHECK (status <> 'verified' OR metric NOT IN (
    'liquid_consumption_l_100km', 'electric_consumption_kwh_100km',
    'electric_range_km', 'co2_g_km'
  ) OR COALESCE(
    context->>'procedure' IN ('WLTP', 'NEDC', 'declared', 'measured')
    AND context->>'cycle' IN ('combined', 'urban', 'highway', 'weighted_combined'),
    false
  )),
  CHECK (supersedes_id IS NULL OR supersedes_id <> id),
  UNIQUE (id, spec_id, metric, context),
  FOREIGN KEY (selected_observation_id, spec_id, metric, context)
    REFERENCES spec_observations (id, spec_id, metric, context) ON DELETE RESTRICT,
  FOREIGN KEY (supersedes_id, spec_id, metric, context)
    REFERENCES fact_decisions (id, spec_id, metric, context) ON DELETE RESTRICT
);

-- One root and at most one successor: concurrent revisions cannot fork a fact.
CREATE UNIQUE INDEX fact_decisions_one_root_idx
  ON fact_decisions (spec_id, metric, context) WHERE supersedes_id IS NULL;

CREATE FUNCTION drivewise_validate_fact_decision() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF cardinality(NEW.evidence_ids) <> (
    SELECT count(DISTINCT observation.id)
    FROM spec_observations observation
    JOIN source_snapshots snapshot ON snapshot.id = observation.snapshot_id
    WHERE observation.id = ANY(NEW.evidence_ids)
      AND observation.spec_id = NEW.spec_id
      AND observation.metric = NEW.metric
      AND observation.context = NEW.context
      AND snapshot.retrieved_at <= NEW.decided_at
  ) THEN
    RAISE EXCEPTION 'Decision evidence must exist, be unique and match its fact and time'
      USING ERRCODE = '23514';
  END IF;
  IF EXISTS (
    SELECT 1 FROM fact_decisions previous
    WHERE previous.id = NEW.supersedes_id AND previous.decided_at > NEW.decided_at
  ) THEN
    RAISE EXCEPTION 'Decision revision predates its predecessor' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER fact_decisions_validate
  BEFORE INSERT ON fact_decisions
  FOR EACH ROW EXECUTE FUNCTION drivewise_validate_fact_decision();

CREATE FUNCTION drivewise_reject_evidence_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'Evidence history is append-only; insert a new revision'
    USING ERRCODE = '23514';
END;
$$;

CREATE TRIGGER source_snapshots_immutable
  BEFORE UPDATE OR DELETE ON source_snapshots
  FOR EACH ROW EXECUTE FUNCTION drivewise_reject_evidence_mutation();
CREATE TRIGGER spec_observations_immutable
  BEFORE UPDATE OR DELETE ON spec_observations
  FOR EACH ROW EXECUTE FUNCTION drivewise_reject_evidence_mutation();
CREATE TRIGGER fact_decisions_immutable
  BEFORE UPDATE OR DELETE ON fact_decisions
  FOR EACH ROW EXECUTE FUNCTION drivewise_reject_evidence_mutation();
