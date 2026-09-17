-- A staged bundle is inert until explicitly published. Legacy rows keep their IDs.
CREATE TABLE catalog_v2_batches (
  id uuid PRIMARY KEY,
  dataset_hash text NOT NULL UNIQUE,
  payload jsonb NOT NULL,
  staged_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz
);

ALTER TABLE vehicles
  ALTER COLUMN model_year DROP NOT NULL,
  ALTER COLUMN body_style DROP NOT NULL,
  ALTER COLUMN fuel_type DROP NOT NULL,
  ADD COLUMN catalog_version integer NOT NULL DEFAULT 1 CHECK (catalog_version IN (1, 2)),
  ADD COLUMN identity_evidence uuid[] NOT NULL DEFAULT '{}',
  ADD COLUMN legacy_record jsonb;

-- Building the new index first fails transactionally on pre-existing collisions.
CREATE UNIQUE INDEX vehicles_identity_v2_key ON vehicles (
  lower(make), lower(model), vehicle_type, generation_key, phase_key,
  body_style, model_year, market
) NULLS NOT DISTINCT;
ALTER TABLE vehicles DROP CONSTRAINT vehicles_make_model_model_year_market_key;

ALTER TABLE vehicle_specs
  ALTER COLUMN trim DROP NOT NULL,
  ALTER COLUMN body_style DROP NOT NULL,
  ALTER COLUMN fuel_type DROP NOT NULL,
  ADD COLUMN catalog_version integer NOT NULL DEFAULT 1 CHECK (catalog_version IN (1, 2)),
  ADD COLUMN fuel text,
  ADD COLUMN engine_code text,
  ADD COLUMN external_references jsonb NOT NULL DEFAULT '[]',
  ADD COLUMN identity_evidence uuid[] NOT NULL DEFAULT '{}',
  ADD COLUMN legacy_record jsonb;

CREATE VIEW catalog_identity_eligibility AS
SELECT s.id AS spec_id,
       cardinality(s.identity_evidence) > 0 AND cardinality(v.identity_evidence) > 0
       AND NOT EXISTS (
         SELECT 1 FROM unnest(s.identity_evidence || v.identity_evidence) evidence(id)
         LEFT JOIN source_snapshots snap ON snap.id = evidence.id
         LEFT JOIN sources source ON source.id = snap.source_id
         WHERE snap.id IS NULL OR snap.evidence_kind <> 'sourced'
           OR source.ranking_permission <> 'permitted'
           OR nullif(trim(source.license), '') IS NULL
       ) AS eligible
FROM vehicle_specs s JOIN vehicles v ON v.id = s.vehicle_id;


-- Heads, including negative decisions, are selected BEFORE eligibility filtering.
-- Source revocation takes effect on the next read; it needs no republishing job.
CREATE VIEW catalog_current_facts AS
SELECT d.*, o.value_min, o.value_max, o.unit,
       o.evidence_excerpt, o.evidence_locator,
       ss.source_url, ss.retrieved_at, ss.content_sha256,
       src.source_key, src.name AS source_name,
       (d.status = 'verified' AND identity.eligible AND NOT EXISTS (
         SELECT 1 FROM spec_observations evidence
         JOIN source_snapshots snap ON snap.id = evidence.snapshot_id
         JOIN sources source ON source.id = snap.source_id
         WHERE evidence.id = ANY(d.evidence_ids)
           AND (source.ranking_permission <> 'permitted'
                OR snap.evidence_kind <> 'sourced'
                OR nullif(trim(source.license), '') IS NULL)
       )) AS eligible
FROM fact_decisions d
JOIN catalog_identity_eligibility identity ON identity.spec_id = d.spec_id
LEFT JOIN spec_observations o ON o.id = d.selected_observation_id
LEFT JOIN source_snapshots ss ON ss.id = o.snapshot_id
LEFT JOIN sources src ON src.id = ss.source_id
WHERE NOT EXISTS (SELECT 1 FROM fact_decisions next WHERE next.supersedes_id = d.id);

-- Legacy consumers cannot flatten intervals or choose between configurations.
-- Only one current context per metric, covering the entire variant, is projected.
CREATE VIEW catalog_scalar_facts AS
SELECT f.*,
       CASE f.metric
         WHEN 'liquid_consumption_l_100km' THEN 'consumption_l_100km'
         WHEN 'electric_consumption_kwh_100km' THEN 'energy_consumption_kwh_100km'
         WHEN 'electric_range_km' THEN 'wltp_range_km'
         ELSE f.metric::text
       END AS legacy_metric
FROM catalog_current_facts f
JOIN vehicle_specs s ON s.id = f.spec_id
WHERE f.eligible AND f.value_min = f.value_max
  AND (SELECT count(*) FROM catalog_current_facts other
       WHERE other.spec_id = f.spec_id AND other.metric = f.metric) = 1
  AND f.context->>'configuration_key' IS NULL
  AND (f.context->>'valid_from' IS NULL OR
       (s.valid_from IS NOT NULL AND (f.context->>'valid_from')::date <= s.valid_from))
  AND (f.context->>'valid_to' IS NULL OR
       (s.valid_to IS NOT NULL AND (f.context->>'valid_to')::date >= s.valid_to))
  AND (f.metric NOT IN ('liquid_consumption_l_100km',
       'electric_consumption_kwh_100km', 'electric_range_km', 'co2_g_km')
       OR (f.context->>'procedure' = 'WLTP' AND f.context->>'cycle' = 'combined'
           AND s.powertrain_type <> 'PHEV'))
  AND (f.metric <> 'cargo_volume_liters' OR
       (f.context->>'method' = 'VDA' AND f.context->>'seating_configuration' = 'all_seats_up'))
  AND (f.metric NOT IN ('seats', 'electric_range_km', 'co2_g_km')
       OR (f.value_min = trunc(f.value_min) AND f.value_min <= 2147483647));

CREATE VIEW catalog_read_specs AS
SELECT s.id,
       s.vehicle_id,
       s.trim,
       s.drivetrain,
       s.transmission,
       s.engine,
       CASE WHEN s.catalog_version = 1 THEN s.horsepower END AS horsepower,
       CASE WHEN s.catalog_version = 1 THEN s.battery_kwh END AS battery_kwh,
       CASE WHEN s.catalog_version = 1 THEN s.consumption_l_100km ELSE (SELECT value_min FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'consumption_l_100km') END AS consumption_l_100km,
       CASE WHEN s.catalog_version = 1 THEN s.wltp_range_km ELSE (SELECT value_min FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'wltp_range_km') END AS wltp_range_km,
       CASE WHEN s.catalog_version = 1 THEN s.co2_g_km ELSE (SELECT value_min FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'co2_g_km') END AS co2_g_km,
       CASE WHEN s.catalog_version = 1 THEN s.euro_emission_standard END AS euro_emission_standard,
       CASE WHEN s.catalog_version = 1 THEN s.seats ELSE (SELECT value_min FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'seats') END AS seats,
       CASE WHEN s.catalog_version = 1 THEN s.cargo_volume_liters ELSE (SELECT value_min FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'cargo_volume_liters') END AS cargo_volume_liters,
       s.metadata,
       s.created_at,
       s.updated_at,
       s.variant_key,
       s.is_default,
       s.body_style,
       s.fuel_type,
       CASE WHEN s.catalog_version = 1 THEN s.list_price_eur END AS list_price_eur,
       CASE WHEN s.catalog_version = 1 THEN s.energy_consumption_kwh_100km ELSE (SELECT value_min FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'energy_consumption_kwh_100km') END AS energy_consumption_kwh_100km,
       s.powertrain_type,
       s.valid_from,
       s.valid_to,
       s.catalog_version,
       s.fuel,
       s.engine_code,
       s.external_references,
       s.identity_evidence,
       s.legacy_record
FROM vehicle_specs s;

-- A shared provenance relation keeps Advisor and Model Analysis on the same rules.
CREATE VIEW catalog_read_provenance AS
SELECT p.spec_id, p.source_id, p.source_url, p.observed_at, p.metadata, p.is_current
FROM vehicle_spec_provenance p
JOIN vehicle_specs s ON s.id = p.spec_id AND s.catalog_version = 1
UNION ALL
SELECT f.spec_id, snap.source_id, f.source_url, f.retrieved_at,
       jsonb_build_object('supported_metrics', jsonb_build_array(f.legacy_metric),
                          'decision_id', f.id, 'observation_id', f.selected_observation_id), true
FROM catalog_scalar_facts f
JOIN spec_observations o ON o.id = f.selected_observation_id
JOIN source_snapshots snap ON snap.id = o.snapshot_id
JOIN vehicle_specs s ON s.id = f.spec_id AND s.catalog_version = 2
UNION ALL
SELECT s.id, snap.source_id, snap.source_url, snap.retrieved_at,
       jsonb_build_object('supported_metrics', jsonb_build_array('body_style', 'fuel_type')), true
FROM vehicle_specs s
JOIN catalog_identity_eligibility identity ON identity.spec_id = s.id AND identity.eligible
JOIN source_snapshots snap ON snap.id = s.identity_evidence[1]
WHERE s.catalog_version = 2;

CREATE FUNCTION drivewise_protect_v2_catalog() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.catalog_version = 2 AND current_setting('drivewise.catalog_writer', true)
      IS DISTINCT FROM 'v2' THEN
    RAISE EXCEPTION 'Catalog v2 records require the v2 publisher' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER vehicles_v2_writer BEFORE UPDATE ON vehicles
  FOR EACH ROW EXECUTE FUNCTION drivewise_protect_v2_catalog();
CREATE TRIGGER vehicle_specs_v2_writer BEFORE UPDATE ON vehicle_specs
  FOR EACH ROW EXECUTE FUNCTION drivewise_protect_v2_catalog();

CREATE VIEW catalog_analysis_specs AS
SELECT s.id,
       s.vehicle_id,
       s.trim,
       s.drivetrain,
       s.transmission,
       s.engine,
       CASE WHEN 'horsepower' = ANY(evidence.metrics) THEN s.horsepower END AS horsepower,
       CASE WHEN 'battery_kwh' = ANY(evidence.metrics) THEN s.battery_kwh END AS battery_kwh,
       CASE WHEN 'consumption_l_100km' = ANY(evidence.metrics) THEN s.consumption_l_100km END AS consumption_l_100km,
       CASE WHEN 'wltp_range_km' = ANY(evidence.metrics) THEN s.wltp_range_km END AS wltp_range_km,
       CASE WHEN 'co2_g_km' = ANY(evidence.metrics) THEN s.co2_g_km END AS co2_g_km,
       s.euro_emission_standard,
       CASE WHEN 'seats' = ANY(evidence.metrics) THEN s.seats END AS seats,
       CASE WHEN 'cargo_volume_liters' = ANY(evidence.metrics) THEN s.cargo_volume_liters END AS cargo_volume_liters,
       s.metadata,
       s.created_at,
       s.updated_at,
       s.variant_key,
       s.is_default,
       CASE WHEN 'body_style' = ANY(evidence.metrics) THEN s.body_style END AS body_style,
       CASE WHEN 'fuel_type' = ANY(evidence.metrics) THEN s.fuel_type END AS fuel_type,
       CASE WHEN 'list_price_eur' = ANY(evidence.metrics) THEN s.list_price_eur END AS list_price_eur,
       CASE WHEN 'energy_consumption_kwh_100km' = ANY(evidence.metrics) THEN s.energy_consumption_kwh_100km END AS energy_consumption_kwh_100km,
       s.powertrain_type,
       s.valid_from,
       s.valid_to,
       s.catalog_version,
       s.fuel,
       s.engine_code,
       s.external_references,
       s.identity_evidence,
       s.legacy_record
FROM catalog_read_specs s
LEFT JOIN LATERAL (
  SELECT array_agg(DISTINCT metric) AS metrics
  FROM catalog_read_provenance p
  JOIN sources src ON src.id = p.source_id
  CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(
    p.metadata->'supported_metrics', p.metadata->'metrics', '[]'::jsonb
  )) metric
  WHERE p.spec_id = s.id AND p.is_current AND src.ranking_permission = 'permitted'
) evidence ON true;

CREATE VIEW catalog_usable_listings AS
SELECT l.* FROM listings l
JOIN sources source ON source.id = l.source_id
JOIN import_runs run ON run.id = l.import_run_id AND run.status = 'completed'
WHERE source.ranking_permission = 'permitted' AND upper(source.market) = 'IT'
  AND nullif(trim(source.name), '') IS NOT NULL
  AND nullif(trim(source.license), '') IS NOT NULL
  AND nullif(trim(l.source_url), '') IS NOT NULL
  AND l.is_active;
