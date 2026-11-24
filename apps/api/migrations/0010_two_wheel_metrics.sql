-- Two-wheel metric registry. Additive: existing evidence keeps its meaning.
-- Wet weight reuses mass_kg with context.method = 'wet'; no new mass metric.
-- Constraint names are the ones 0008 generated; a mismatch fails this migration.
ALTER DOMAIN catalog_metric DROP CONSTRAINT catalog_metric_check;
ALTER DOMAIN catalog_metric ADD CONSTRAINT catalog_metric_check CHECK (VALUE IN (
  'engine_power_kw', 'system_power_kw', 'continuous_power_kw',
  'engine_displacement_cc', 'cylinders', 'battery_gross_kwh',
  'battery_usable_kwh', 'liquid_consumption_l_100km',
  'electric_consumption_kwh_100km', 'electric_range_km', 'co2_g_km',
  'length_mm', 'body_width_mm', 'width_with_mirrors_mm', 'height_mm',
  'seats', 'cargo_volume_liters', 'mass_kg', 'ac_charge_power_kw',
  'dc_peak_charge_power_kw',
  'seat_height_mm', 'fuel_tank_capacity_liters', 'underseat_storage_liters'
));

-- The previous CASE yielded NULL for unlisted metrics, which a CHECK accepts.
ALTER TABLE spec_observations DROP CONSTRAINT spec_observations_check7;
ALTER TABLE spec_observations ADD CONSTRAINT spec_observations_unit_check CHECK (
  unit IS NOT DISTINCT FROM CASE
    WHEN metric IN ('engine_power_kw', 'system_power_kw', 'continuous_power_kw',
                    'ac_charge_power_kw', 'dc_peak_charge_power_kw') THEN 'kW'
    WHEN metric IN ('battery_gross_kwh', 'battery_usable_kwh') THEN 'kWh'
    WHEN metric IN ('length_mm', 'body_width_mm', 'width_with_mirrors_mm',
                    'height_mm', 'seat_height_mm') THEN 'mm'
    WHEN metric IN ('seats', 'cylinders') THEN 'count'
    WHEN metric = 'engine_displacement_cc' THEN 'cm3'
    WHEN metric = 'liquid_consumption_l_100km' THEN 'l/100km'
    WHEN metric = 'electric_consumption_kwh_100km' THEN 'kWh/100km'
    WHEN metric = 'electric_range_km' THEN 'km'
    WHEN metric = 'co2_g_km' THEN 'g/km'
    WHEN metric IN ('cargo_volume_liters', 'fuel_tank_capacity_liters',
                    'underseat_storage_liters') THEN 'l'
    WHEN metric = 'mass_kg' THEN 'kg'
  END
);
