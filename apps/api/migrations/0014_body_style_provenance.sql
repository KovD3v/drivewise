-- A later bundle may fill an unknown body style by appending to the vehicle's
-- identity evidence the snapshot that states it (catalog v2, "Identity migration
-- and ownership"). The read provenance credited body style and fuel type alike to
-- the first identity snapshot of the variant, so a filled body style still named
-- the vehicle's original source. Body style is now credited to the vehicle's last
-- identity snapshot, the one appended with it; fuel type keeps the variant's first.
-- A vehicle without a body style gets no body-style credit.
-- Same columns as 0009, as CREATE OR REPLACE VIEW requires.
CREATE OR REPLACE VIEW catalog_read_provenance AS
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
