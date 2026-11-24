-- Read-path rewrite of the v2 scalar views, with the same eligibility rules as 0012.
-- 1. catalog_scalar_facts counts the current contexts of a metric with one window
--    pass, instead of one correlated count per fact. The count still runs over every
--    current fact (eligible or not), as before. The columns of catalog_current_facts
--    are listed because the window column must not leak into the view.
-- 2. catalog_read_specs pivots the scalar facts of a v2 spec in one lateral
--    aggregate, instead of nine correlated subqueries per row. A metric has at most
--    one scalar fact per spec (the count above), so max() picks that fact.
-- 3. v2 specs now publish the dimensions and the power that GET /vehicles/{id}
--    already read from reviewed facts, so the Advisor (Garage Fit, TCO) reads the
--    same values: length, body width, height and displacement as whole numbers,
--    power as the system power, or the engine power when the engine is the one motor.
-- 4. catalog_read_provenance credits those v2 facts under the read-column names
--    as well (width_mm, displacement_cc, power_kw), because consumers trust a value
--    only when a source names its column.
-- Same columns, names, types and order as before, as CREATE OR REPLACE VIEW requires.
CREATE OR REPLACE VIEW catalog_scalar_facts AS
SELECT f.id, f.spec_id, f.metric, f.context, f.status, f.selected_observation_id,
       f.evidence_ids, f.supersedes_id, f.reason, f.actor_kind, f.actor_id,
       f.policy_version, f.decided_at, f.value_min, f.value_max, f.unit,
       f.evidence_excerpt, f.evidence_locator, f.source_url, f.retrieved_at,
       f.content_sha256, f.source_key, f.source_name, f.eligible,
       CASE f.metric
         WHEN 'liquid_consumption_l_100km' THEN 'consumption_l_100km'
         WHEN 'electric_consumption_kwh_100km' THEN 'energy_consumption_kwh_100km'
         WHEN 'electric_range_km' THEN 'wltp_range_km'
         ELSE f.metric::text
       END AS legacy_metric,
       CASE WHEN f.value_min = f.value_max THEN f.value_min ELSE f.value_max END AS scalar_value,
       CASE WHEN f.value_min = f.value_max THEN 'exact' ELSE 'interval_upper' END AS scalar_basis
FROM (
  SELECT current_fact.*,
         count(*) OVER (PARTITION BY current_fact.spec_id, current_fact.metric)
           AS metric_contexts
  FROM catalog_current_facts current_fact
) f
JOIN vehicle_specs s ON s.id = f.spec_id
WHERE f.eligible
  AND f.metric_contexts = 1
  AND (f.value_min = f.value_max OR f.metric IN ('liquid_consumption_l_100km',
       'electric_consumption_kwh_100km'))
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

CREATE OR REPLACE VIEW catalog_read_specs AS
SELECT s.id,
       s.vehicle_id,
       s.trim,
       s.drivetrain,
       s.transmission,
       s.engine,
       CASE WHEN s.catalog_version = 1 THEN s.horsepower END AS horsepower,
       CASE WHEN s.catalog_version = 1 THEN s.battery_kwh END AS battery_kwh,
       CASE WHEN s.catalog_version = 1 THEN s.consumption_l_100km ELSE fact.consumption_l_100km END AS consumption_l_100km,
       CASE WHEN s.catalog_version = 1 THEN s.wltp_range_km ELSE fact.wltp_range_km END AS wltp_range_km,
       CASE WHEN s.catalog_version = 1 THEN s.co2_g_km ELSE fact.co2_g_km END AS co2_g_km,
       CASE WHEN s.catalog_version = 1 THEN s.euro_emission_standard END AS euro_emission_standard,
       CASE WHEN s.catalog_version = 1 THEN s.seats ELSE fact.seats END AS seats,
       CASE WHEN s.catalog_version = 1 THEN s.cargo_volume_liters ELSE fact.cargo_volume_liters END AS cargo_volume_liters,
       s.metadata,
       s.created_at,
       s.updated_at,
       s.variant_key,
       s.is_default,
       s.body_style,
       s.fuel_type,
       CASE WHEN s.catalog_version = 1 THEN s.list_price_eur ELSE fact.list_price_eur END AS list_price_eur,
       CASE WHEN s.catalog_version = 1 THEN s.energy_consumption_kwh_100km ELSE fact.energy_consumption_kwh_100km END AS energy_consumption_kwh_100km,
       s.powertrain_type,
       s.valid_from,
       s.valid_to,
       s.catalog_version,
       s.fuel,
       s.engine_code,
       s.external_references,
       s.identity_evidence,
       s.legacy_record,
       -- Knowledge-profile fields (0005) stay v1-only, except the reviewed v2
       -- dimensions, displacement and power below.
       CASE WHEN s.catalog_version = 1 THEN s.generation_name END AS generation_name,
       CASE WHEN s.catalog_version = 1 THEN s.restyling_label END AS restyling_label,
       CASE WHEN s.catalog_version = 1 THEN s.category END AS category,
       CASE WHEN s.catalog_version = 1 THEN s.doors END AS doors,
       CASE WHEN s.catalog_version = 1 THEN s.length_mm ELSE fact.length_mm END AS length_mm,
       CASE WHEN s.catalog_version = 1 THEN s.width_mm ELSE fact.width_mm END AS width_mm,
       CASE WHEN s.catalog_version = 1 THEN s.height_mm ELSE fact.height_mm END AS height_mm,
       CASE WHEN s.catalog_version = 1 THEN s.wheelbase_mm END AS wheelbase_mm,
       -- Mass in running order is not curb weight: v2 has no curb weight yet.
       CASE WHEN s.catalog_version = 1 THEN s.curb_weight_kg END AS curb_weight_kg,
       CASE WHEN s.catalog_version = 1 THEN s.gross_weight_kg END AS gross_weight_kg,
       CASE WHEN s.catalog_version = 1 THEN s.payload_kg END AS payload_kg,
       CASE WHEN s.catalog_version = 1 THEN s.displacement_cc ELSE fact.displacement_cc END AS displacement_cc,
       CASE WHEN s.catalog_version = 1 THEN s.cylinders END AS cylinders,
       CASE WHEN s.catalog_version = 1 THEN s.power_kw ELSE fact.power_kw END AS power_kw,
       CASE WHEN s.catalog_version = 1 THEN s.torque_nm END AS torque_nm,
       CASE WHEN s.catalog_version = 1 THEN s.battery_usable_kwh END AS battery_usable_kwh,
       CASE WHEN s.catalog_version = 1 THEN s.transmission_type END AS transmission_type,
       CASE WHEN s.catalog_version = 1 THEN s.gear_count END AS gear_count,
       CASE WHEN s.catalog_version = 1 THEN s.differential_type END AS differential_type,
       CASE WHEN s.catalog_version = 1 THEN s.acceleration_0_100_s END AS acceleration_0_100_s,
       CASE WHEN s.catalog_version = 1 THEN s.top_speed_kmh END AS top_speed_kmh,
       CASE WHEN s.catalog_version = 1 THEN s.braking_100_0_m END AS braking_100_0_m,
       CASE WHEN s.catalog_version = 1 THEN s.homologation_cycle END AS homologation_cycle,
       -- ADR-018: 'interval_upper' when the published v2 consumption is the upper
       -- value of an interval, 'exact' for a point value, NULL for v1 or no value.
       fact.consumption_l_100km_basis,
       fact.energy_consumption_kwh_100km_basis
FROM vehicle_specs s
LEFT JOIN LATERAL (
  SELECT
    max(f.scalar_value) FILTER (WHERE f.legacy_metric = 'consumption_l_100km') AS consumption_l_100km,
    max(f.scalar_value) FILTER (WHERE f.legacy_metric = 'wltp_range_km') AS wltp_range_km,
    max(f.scalar_value) FILTER (WHERE f.legacy_metric = 'co2_g_km') AS co2_g_km,
    max(f.scalar_value) FILTER (WHERE f.legacy_metric = 'seats') AS seats,
    max(f.scalar_value) FILTER (WHERE f.legacy_metric = 'cargo_volume_liters') AS cargo_volume_liters,
    max(f.scalar_value) FILTER (WHERE f.legacy_metric = 'list_price_eur') AS list_price_eur,
    max(f.scalar_value) FILTER (WHERE f.legacy_metric = 'energy_consumption_kwh_100km') AS energy_consumption_kwh_100km,
    max(f.scalar_basis) FILTER (WHERE f.legacy_metric = 'consumption_l_100km') AS consumption_l_100km_basis,
    max(f.scalar_basis) FILTER (WHERE f.legacy_metric = 'energy_consumption_kwh_100km') AS energy_consumption_kwh_100km_basis,
    -- The integer read columns take only whole values that fit an integer.
    (max(f.scalar_value) FILTER (WHERE f.metric = 'length_mm' AND f.whole))::integer AS length_mm,
    (max(f.scalar_value) FILTER (WHERE f.metric = 'body_width_mm' AND f.whole))::integer AS width_mm,
    (max(f.scalar_value) FILTER (WHERE f.metric = 'height_mm' AND f.whole))::integer AS height_mm,
    (max(f.scalar_value) FILTER (WHERE f.metric = 'engine_displacement_cc' AND f.whole))::integer AS displacement_cc,
    -- Vehicle power: the system power, else the engine power of a combustion-only car.
    COALESCE(
      max(f.scalar_value) FILTER (WHERE f.metric = 'system_power_kw'),
      max(f.scalar_value) FILTER (WHERE f.metric = 'engine_power_kw' AND s.powertrain_type = 'ICE')
    ) AS power_kw
  FROM (
    SELECT scalar.metric, scalar.legacy_metric, scalar.scalar_value, scalar.scalar_basis,
           scalar.scalar_value = trunc(scalar.scalar_value)
             AND scalar.scalar_value <= 2147483647 AS whole
    FROM catalog_scalar_facts scalar
    WHERE scalar.spec_id = s.id
  ) f
  WHERE s.catalog_version = 2
) fact ON true;

CREATE OR REPLACE VIEW catalog_read_provenance AS
SELECT p.spec_id, p.source_id, p.source_url, p.observed_at, p.metadata, p.is_current
FROM vehicle_spec_provenance p
JOIN vehicle_specs s ON s.id = p.spec_id AND s.catalog_version = 1
UNION ALL
SELECT f.spec_id, snap.source_id, f.source_url, f.retrieved_at,
       jsonb_build_object(
         'supported_metrics',
         jsonb_build_array(f.legacy_metric) || CASE
           WHEN f.metric = 'body_width_mm' THEN jsonb_build_array('width_mm')
           WHEN f.metric = 'engine_displacement_cc' THEN jsonb_build_array('displacement_cc')
           WHEN f.metric = 'system_power_kw' THEN jsonb_build_array('power_kw')
           WHEN f.metric = 'engine_power_kw' AND s.powertrain_type = 'ICE'
             AND NOT EXISTS (
               SELECT 1 FROM catalog_scalar_facts system_power
               WHERE system_power.spec_id = f.spec_id
                 AND system_power.metric = 'system_power_kw'
             ) THEN jsonb_build_array('power_kw')
           ELSE '[]'::jsonb
         END,
         'decision_id', f.id, 'observation_id', f.selected_observation_id), true
FROM catalog_scalar_facts f
JOIN spec_observations o ON o.id = f.selected_observation_id
JOIN source_snapshots snap ON snap.id = o.snapshot_id
JOIN vehicle_specs s ON s.id = f.spec_id AND s.catalog_version = 2
UNION ALL
SELECT s.id, snap.source_id, snap.source_url, snap.retrieved_at,
       jsonb_build_object('supported_metrics', jsonb_build_array('fuel_type')), true
FROM vehicle_specs s
JOIN catalog_identity_eligibility identity ON identity.spec_id = s.id AND identity.eligible
JOIN source_snapshots snap ON snap.id = s.identity_evidence[1]
WHERE s.catalog_version = 2
UNION ALL
SELECT s.id, snap.source_id, snap.source_url, snap.retrieved_at,
       jsonb_build_object('supported_metrics', jsonb_build_array('body_style')), true
FROM vehicle_specs s
JOIN vehicles v ON v.id = s.vehicle_id AND v.body_style IS NOT NULL
JOIN catalog_identity_eligibility identity ON identity.spec_id = s.id AND identity.eligible
JOIN source_snapshots snap
  ON snap.id = v.identity_evidence[cardinality(v.identity_evidence)]
WHERE s.catalog_version = 2;
