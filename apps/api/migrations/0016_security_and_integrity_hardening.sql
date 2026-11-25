-- Security and integrity hardening of the catalog evidence and session tables.
-- Additive: no existing row changes; a migration that finds bad rows stops with a
-- clear error instead of rewriting append-only history.
-- 1. TRUNCATE no longer bypasses the append-only evidence triggers (L9).
-- 2. Snapshot URLs are HTTPS only, like every other provenance URL since 0007.
-- 3. A decision's valid_from and valid_to are real ISO dates, so the ::date casts
--    of catalog_scalar_facts can never fail on a stored row (L12).
-- 4. Only a human or rule decision makes a fact eligible for ranking: an agent
--    decision needs a human or rule sign-off first (M3).
-- 5. Lookup indexes for fact reads and for the 30-day session retention purge.

-- 1. Row triggers do not fire on TRUNCATE; a statement trigger does, also when
--    the table is reached through TRUNCATE ... CASCADE.
CREATE TRIGGER source_snapshots_no_truncate
  BEFORE TRUNCATE ON source_snapshots
  FOR EACH STATEMENT EXECUTE FUNCTION drivewise_reject_evidence_mutation();
CREATE TRIGGER spec_observations_no_truncate
  BEFORE TRUNCATE ON spec_observations
  FOR EACH STATEMENT EXECUTE FUNCTION drivewise_reject_evidence_mutation();
CREATE TRIGGER fact_decisions_no_truncate
  BEFORE TRUNCATE ON fact_decisions
  FOR EACH STATEMENT EXECUTE FUNCTION drivewise_reject_evidence_mutation();

-- 2. Snapshots are immutable, so a plain-HTTP row cannot be repaired here: stop
--    with a clear message and let a person decide.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM source_snapshots WHERE source_url !~ '^https://[^/[:space:]]+'
  ) THEN
    RAISE EXCEPTION 'source_snapshots contains a non-HTTPS source_url';
  END IF;
END;
$$;

ALTER TABLE source_snapshots
  DROP CONSTRAINT source_snapshots_source_url_check,
  ADD CONSTRAINT source_snapshots_source_url_check
    CHECK (source_url ~ '^https://[^/[:space:]]+');

-- 3. True for a calendar date written YYYY-MM-DD. Malformed input is false, never
--    an error, like catalog_list_price_valid in 0011.
CREATE FUNCTION catalog_iso_date_valid(value text)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
  IF value IS NULL OR value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN
    RETURN false;
  END IF;
  -- A calendar date: 2026-02-30 raises here and returns false below.
  PERFORM value::date;
  RETURN true;
EXCEPTION WHEN data_exception THEN
  RETURN false;
END;
$$;

ALTER TABLE fact_decisions ADD CONSTRAINT fact_decisions_validity_dates_check CHECK (
  (coalesce(jsonb_typeof(context->'valid_from'), 'null') = 'null'
   OR catalog_iso_date_valid(context->>'valid_from'))
  AND (coalesce(jsonb_typeof(context->'valid_to'), 'null') = 'null'
   OR catalog_iso_date_valid(context->>'valid_to'))
);

-- 4. Same columns, names, types and order as 0009, as CREATE OR REPLACE VIEW
--    requires; only the eligible expression gains the actor rule.
CREATE OR REPLACE VIEW catalog_current_facts AS
SELECT d.*, o.value_min, o.value_max, o.unit,
       o.evidence_excerpt, o.evidence_locator,
       ss.source_url, ss.retrieved_at, ss.content_sha256,
       src.source_key, src.name AS source_name,
       (d.status = 'verified' AND d.actor_kind IN ('human', 'rule')
        AND identity.eligible AND NOT EXISTS (
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

-- 5. Fact lookups by spec and metric, and the retention purge by age.
CREATE INDEX IF NOT EXISTS idx_fact_decisions_spec_metric
  ON fact_decisions (spec_id, metric);
CREATE INDEX IF NOT EXISTS idx_guided_decisions_updated_at
  ON guided_decisions (updated_at);
CREATE INDEX IF NOT EXISTS idx_recommendation_runs_created_at
  ON recommendation_runs (created_at);
