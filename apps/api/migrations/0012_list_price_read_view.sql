-- v2 specs expose list_price_eur from an eligible list-price fact, under the same
-- permitted, sourced and licensed rule as every other v2 scalar; v1 rows keep their
-- stored value. Every v2 scalar now reads scalar_value (ADR-018, below), and two
-- basis columns are appended. catalog_analysis_specs and catalog_read_provenance
-- pick the changes up through the shared views.
-- ADR-018: an interval consumption is published at its upper value, so running
-- costs are not understated. Only liquid and electric consumption; every other
-- interval still stays out of the scalar reads. scalar_value is what the read
-- catalogue publishes and scalar_basis says whether it is exact or an upper value.
-- The new columns are appended, as CREATE OR REPLACE VIEW requires.
CREATE OR REPLACE VIEW catalog_scalar_facts AS
SELECT f.*,
       CASE f.metric
         WHEN 'liquid_consumption_l_100km' THEN 'consumption_l_100km'
         WHEN 'electric_consumption_kwh_100km' THEN 'energy_consumption_kwh_100km'
         WHEN 'electric_range_km' THEN 'wltp_range_km'
         ELSE f.metric::text
       END AS legacy_metric,
       CASE WHEN f.value_min = f.value_max THEN f.value_min ELSE f.value_max END AS scalar_value,
       CASE WHEN f.value_min = f.value_max THEN 'exact' ELSE 'interval_upper' END AS scalar_basis
FROM catalog_current_facts f
JOIN vehicle_specs s ON s.id = f.spec_id
WHERE f.eligible
  AND (f.value_min = f.value_max OR f.metric IN ('liquid_consumption_l_100km',
       'electric_consumption_kwh_100km'))
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

CREATE OR REPLACE VIEW catalog_read_specs AS
SELECT s.id,
       s.vehicle_id,
       s.trim,
       s.drivetrain,
       s.transmission,
       s.engine,
       CASE WHEN s.catalog_version = 1 THEN s.horsepower END AS horsepower,
       CASE WHEN s.catalog_version = 1 THEN s.battery_kwh END AS battery_kwh,
       CASE WHEN s.catalog_version = 1 THEN s.consumption_l_100km ELSE (SELECT scalar_value FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'consumption_l_100km') END AS consumption_l_100km,
       CASE WHEN s.catalog_version = 1 THEN s.wltp_range_km ELSE (SELECT scalar_value FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'wltp_range_km') END AS wltp_range_km,
       CASE WHEN s.catalog_version = 1 THEN s.co2_g_km ELSE (SELECT scalar_value FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'co2_g_km') END AS co2_g_km,
       CASE WHEN s.catalog_version = 1 THEN s.euro_emission_standard END AS euro_emission_standard,
       CASE WHEN s.catalog_version = 1 THEN s.seats ELSE (SELECT scalar_value FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'seats') END AS seats,
       CASE WHEN s.catalog_version = 1 THEN s.cargo_volume_liters ELSE (SELECT scalar_value FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'cargo_volume_liters') END AS cargo_volume_liters,
       s.metadata,
       s.created_at,
       s.updated_at,
       s.variant_key,
       s.is_default,
       s.body_style,
       s.fuel_type,
       CASE WHEN s.catalog_version = 1 THEN s.list_price_eur ELSE (SELECT scalar_value FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'list_price_eur') END AS list_price_eur,
       CASE WHEN s.catalog_version = 1 THEN s.energy_consumption_kwh_100km ELSE (SELECT scalar_value FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'energy_consumption_kwh_100km') END AS energy_consumption_kwh_100km,
       s.powertrain_type,
       s.valid_from,
       s.valid_to,
       s.catalog_version,
       s.fuel,
       s.engine_code,
       s.external_references,
       s.identity_evidence,
       s.legacy_record,
       -- Knowledge-profile fields (0005) are exposed for v1 rows only; v2 needs reviewed facts.
       CASE WHEN s.catalog_version = 1 THEN s.generation_name END AS generation_name,
       CASE WHEN s.catalog_version = 1 THEN s.restyling_label END AS restyling_label,
       CASE WHEN s.catalog_version = 1 THEN s.category END AS category,
       CASE WHEN s.catalog_version = 1 THEN s.doors END AS doors,
       CASE WHEN s.catalog_version = 1 THEN s.length_mm END AS length_mm,
       CASE WHEN s.catalog_version = 1 THEN s.width_mm END AS width_mm,
       CASE WHEN s.catalog_version = 1 THEN s.height_mm END AS height_mm,
       CASE WHEN s.catalog_version = 1 THEN s.wheelbase_mm END AS wheelbase_mm,
       CASE WHEN s.catalog_version = 1 THEN s.curb_weight_kg END AS curb_weight_kg,
       CASE WHEN s.catalog_version = 1 THEN s.gross_weight_kg END AS gross_weight_kg,
       CASE WHEN s.catalog_version = 1 THEN s.payload_kg END AS payload_kg,
       CASE WHEN s.catalog_version = 1 THEN s.displacement_cc END AS displacement_cc,
       CASE WHEN s.catalog_version = 1 THEN s.cylinders END AS cylinders,
       CASE WHEN s.catalog_version = 1 THEN s.power_kw END AS power_kw,
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
       CASE WHEN s.catalog_version = 2 THEN (SELECT scalar_basis FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'consumption_l_100km') END AS consumption_l_100km_basis,
       CASE WHEN s.catalog_version = 2 THEN (SELECT scalar_basis FROM catalog_scalar_facts WHERE spec_id = s.id AND legacy_metric = 'energy_consumption_kwh_100km') END AS energy_consumption_kwh_100km_basis
FROM vehicle_specs s;

-- Model Analysis reads the same bases, gated like the values they describe.
CREATE OR REPLACE VIEW catalog_analysis_specs AS
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
       s.legacy_record,
       CASE WHEN 'consumption_l_100km' = ANY(evidence.metrics) THEN s.consumption_l_100km_basis END AS consumption_l_100km_basis,
       CASE WHEN 'energy_consumption_kwh_100km' = ANY(evidence.metrics) THEN s.energy_consumption_kwh_100km_basis END AS energy_consumption_kwh_100km_basis
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
