DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM vehicle_provenance
    WHERE source_url !~ '^https://[^[:space:]]+'
  ) THEN
    RAISE EXCEPTION 'vehicle_provenance contains a non-HTTPS source_url';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM vehicle_spec_provenance
    WHERE source_url !~ '^https://[^[:space:]]+'
  ) THEN
    RAISE EXCEPTION 'vehicle_spec_provenance contains a non-HTTPS source_url';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM listings
    WHERE source_url IS NOT NULL
      AND source_url !~ '^https://[^[:space:]]+'
  ) THEN
    RAISE EXCEPTION 'listings contains a non-HTTPS source_url';
  END IF;
END
$$;

ALTER TABLE vehicle_provenance
  DROP CONSTRAINT IF EXISTS vehicle_provenance_source_https_check,
  ADD CONSTRAINT vehicle_provenance_source_https_check
    CHECK (source_url ~ '^https://[^[:space:]]+');

ALTER TABLE vehicle_spec_provenance
  DROP CONSTRAINT IF EXISTS vehicle_spec_provenance_source_https_check,
  ADD CONSTRAINT vehicle_spec_provenance_source_https_check
    CHECK (source_url ~ '^https://[^[:space:]]+');

ALTER TABLE listings
  DROP CONSTRAINT IF EXISTS listings_source_https_check,
  ADD CONSTRAINT listings_source_https_check
    CHECK (source_url IS NULL OR source_url ~ '^https://[^[:space:]]+');
