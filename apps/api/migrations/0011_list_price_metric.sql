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

-- The SQL twin of ListPriceTerms: required keys and types, basis/rate/charge
-- consistency, a real calendar date, and the VAT-inclusive amount the terms imply.
-- PostgreSQL's round() on numeric rounds half away from zero, like Python's
-- ROUND_HALF_UP on these positive amounts. Malformed input is false, never an error.
CREATE FUNCTION catalog_list_price_valid(terms jsonb, amount numeric)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
  basis text;
  printed numeric;
  rate numeric;
  charge numeric;
  charge_with_vat boolean;
  expected numeric;
BEGIN
  IF jsonb_typeof(terms) IS DISTINCT FROM 'object' THEN
    RETURN false;
  END IF;
  basis := terms->>'printed_basis';
  IF basis IS NULL OR basis NOT IN ('incl_vat', 'excl_vat', 'turnkey')
     OR jsonb_typeof(terms->'trim_label') IS DISTINCT FROM 'string'
     OR trim(terms->>'trim_label') = ''
     OR jsonb_typeof(terms->'price_list_valid_from') IS DISTINCT FROM 'string'
     OR terms->>'price_list_valid_from' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     OR coalesce(jsonb_typeof(terms->'substitute_note'), 'null') NOT IN ('string', 'null')
     OR jsonb_typeof(terms->'printed_amount_eur') NOT IN ('string', 'number')
     OR coalesce(jsonb_typeof(terms->'vat_rate_percent'), 'null') NOT IN ('string', 'number', 'null')
     OR coalesce(jsonb_typeof(terms->'on_road_charge_eur'), 'null') NOT IN ('string', 'number', 'null')
     OR coalesce(jsonb_typeof(terms->'on_road_charge_includes_vat'), 'null') NOT IN ('boolean', 'null') THEN
    RETURN false;
  END IF;
  -- A calendar date: 2026-02-30 raises here and returns false below.
  PERFORM (terms->>'price_list_valid_from')::date;
  printed := (terms->>'printed_amount_eur')::numeric;
  rate := (terms->>'vat_rate_percent')::numeric;
  charge := (terms->>'on_road_charge_eur')::numeric;
  charge_with_vat := (terms->>'on_road_charge_includes_vat')::boolean;
  -- NaN sorts above every number and Infinity is not below the limit.
  IF NOT (printed > 0 AND printed < 1e10 AND printed = round(printed, 2))
     OR (basis = 'turnkey') <> (charge IS NOT NULL AND charge_with_vat IS NOT NULL)
     OR (charge IS NOT NULL AND NOT (charge > 0 AND charge < 1e10 AND charge = round(charge, 2)))
     OR (basis = 'excl_vat' OR (basis = 'turnkey' AND NOT charge_with_vat)) <> (rate IS NOT NULL)
     OR (rate IS NOT NULL AND NOT (rate > 0 AND rate < 100 AND rate = round(rate, 2))) THEN
    RETURN false;
  END IF;
  expected := CASE basis
    WHEN 'incl_vat' THEN printed
    WHEN 'excl_vat' THEN round(printed * (100 + rate) / 100, 2)
    ELSE printed - CASE WHEN charge_with_vat THEN charge
                        ELSE round(charge * (100 + rate) / 100, 2) END
  END;
  RETURN expected > 0 AND amount = expected;
EXCEPTION WHEN data_exception THEN
  RETURN false;
END;
$$;

ALTER TABLE spec_observations ADD CONSTRAINT spec_observations_list_price_check CHECK ((
  (metric = 'list_price_eur') = (list_price IS NOT NULL)
  AND (list_price IS NULL OR (
    -- An exact price in cents, like the legacy numeric(12, 2) column.
    value_min = value_max AND catalog_list_price_valid(list_price, value_min)
  ))
) IS TRUE);
