-- Public list price including VAT (ADR-015). Additive: existing evidence keeps its meaning.
-- The price row's terms (printed basis, VAT rate, trim label, price-list date,
-- substitute note) are stored on the observation, not in the fact context, so a
-- new price list supersedes the old decision instead of adding a second context.
ALTER DOMAIN catalog_metric DROP CONSTRAINT catalog_metric_check;
ALTER DOMAIN catalog_metric ADD CONSTRAINT catalog_metric_check CHECK (VALUE IN (
  'engine_power_kw', 'system_power_kw', 'continuous_power_kw',
  'engine_displacement_cc', 'cylinders', 'battery_gross_kwh',
  'battery_usable_kwh', 'liquid_consumption_l_100km',
  'electric_consumption_kwh_100km', 'electric_range_km', 'co2_g_km',
  'length_mm', 'body_width_mm', 'width_with_mirrors_mm', 'height_mm',
  'seats', 'cargo_volume_liters', 'mass_kg', 'ac_charge_power_kw',
  'dc_peak_charge_power_kw',
  'seat_height_mm', 'fuel_tank_capacity_liters', 'underseat_storage_liters',
  'list_price_eur'
));

ALTER TABLE spec_observations DROP CONSTRAINT spec_observations_unit_check;
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
    WHEN metric = 'list_price_eur' THEN 'EUR'
  END
);

ALTER TABLE spec_observations ADD COLUMN list_price jsonb;
ALTER TABLE spec_observations ADD CONSTRAINT spec_observations_list_price_check CHECK (
  (metric = 'list_price_eur') = (list_price IS NOT NULL)
  AND (list_price IS NULL OR (
    jsonb_typeof(list_price) = 'object'
    AND list_price->>'printed_basis' IN ('incl_vat', 'excl_vat')
    AND nullif(trim(list_price->>'trim_label'), '') IS NOT NULL
    AND list_price->>'price_list_valid_from' IS NOT NULL
    -- An exact price in cents, like the legacy numeric(12, 2) column.
    AND value_min = value_max AND value_min = round(value_min, 2)
  ))
);
