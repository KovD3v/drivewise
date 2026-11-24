-- The v2 publisher wrote fuel_type 'phev' for every plug-in hybrid, a value the
-- Advisor does not know, so petrol plug-ins never ranked. Publication now writes
-- the Advisor's names; this moves the rows already published to the same values,
-- so a later bundle with the same variant still matches its published identity.
-- A diesel plug-in becomes 'plug_in_hybrid_diesel', which the Advisor counts as
-- an unsupported fuel; an unknown plug-in fuel stays 'phev'.
SELECT set_config('drivewise.catalog_writer', 'v2', true);
UPDATE vehicle_specs
SET fuel_type = CASE fuel
                  WHEN 'petrol' THEN 'plug_in_hybrid_petrol'
                  WHEN 'diesel' THEN 'plug_in_hybrid_diesel'
                END
WHERE catalog_version = 2 AND powertrain_type = 'PHEV' AND fuel_type = 'phev'
  AND fuel IN ('petrol', 'diesel');
-- Restore the guard for the rest of the transaction: the v1 writer stays blocked.
SELECT set_config('drivewise.catalog_writer', '', true);
