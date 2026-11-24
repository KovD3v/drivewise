from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.repositories.filters import CAR_ONLY_SQL
from app.repositories.list_price import (
    LIST_PRICE_COLUMNS,
    LIST_PRICE_FACT_JOIN,
    list_price_block,
)
from app.schemas.advisor import AdvisorRecommendationGroup, AdvisorRecommendationItem
from app.services.advisor.scoring import FRESHNESS_DAYS, SCORING_VERSION


_CANDIDATE_SPEC_COLUMNS = """
            SELECT
              v.id AS vehicle_id,
              v.canonical_key,
              v.model_family_key,
              v.make,
              v.model,
              v.model_year,
              v.catalog_version, v.vehicle_type, v.generation_key, v.phase_key,
              v.body_style AS vehicle_body_style,
              v.fuel_type AS vehicle_fuel_type,
              v.market,
              v.base_price_eur,
              s.id AS spec_id,
              s.variant_key,
              s.catalog_version AS spec_catalog_version,
              s.powertrain_type,
              s.fuel,
              s.engine_code,
              s.valid_from,
              s.valid_to,
              s.external_references,
              s.is_default,
              s.trim,
              s.body_style AS spec_body_style,
              s.fuel_type AS spec_fuel_type,
              s.list_price_eur,
              s.drivetrain,
              s.transmission,
              s.engine,
              s.horsepower,
              s.battery_kwh,
              s.energy_consumption_kwh_100km,
              s.consumption_l_100km,
              s.consumption_l_100km_basis,
              s.energy_consumption_kwh_100km_basis,
              s.wltp_range_km,
              s.co2_g_km,
              s.euro_emission_standard,
              s.seats,
              s.cargo_volume_liters,
              s.generation_name,
              s.restyling_label,
              s.category,
              s.length_mm,
              s.width_mm,
              s.height_mm,
              s.curb_weight_kg,
              s.engine_code,
              s.power_kw,
              s.transmission_type,
              s.acceleration_0_100_s,
              s.top_speed_kmh,
              s.braking_100_0_m,
"""

_CANDIDATE_LISTING_COLUMNS = """              l.id AS listing_id,
              l.source_id,
              l.listing_ref,
              l.title,
              l.price_eur,
              l.mileage,
              l.condition,
              l.location_region,
              l.source_url,
              l.listed_at,
              l.last_seen_at,
              l.valid_until,
              l.is_active,
              listing_source.name AS listing_source_name,
              listing_source.license AS listing_source_license,
              listing_source.ranking_permission AS listing_source_ranking_permission,
              import_run.status AS import_status,
"""

_CANDIDATE_CHILDREN = """              COALESCE(
                (
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'source_name', provenance_source.name,
                      'source_url', provenance.source_url,
                      'source_license', provenance_source.license,
                      'observed_at', provenance.observed_at,
                      'metadata', provenance.metadata
                    )
                    ORDER BY provenance_source.name, provenance.source_url
                  )
                  FROM catalog_read_provenance AS provenance
                  JOIN sources AS provenance_source
                    ON provenance_source.id = provenance.source_id
                  WHERE provenance.spec_id = s.id
                    AND provenance.is_current
                    AND provenance_source.ranking_permission = 'permitted'
                ),
                '[]'::jsonb
              ) AS spec_provenance
              ,COALESCE(
                (
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', item.id,
                      'operation_code', item.operation_code,
                      'title', item.title,
                      'interval_km', item.interval_km,
                      'interval_months', item.interval_months,
                      'notes', item.notes,
                      'source_id', item.source_id,
                      'source_name', item_source.name,
                      'source_url', item.source_url,
                      'observed_at', item.observed_at
                    ) ORDER BY item.operation_code, item.id
                  )
                  FROM vehicle_maintenance_items AS item
                  JOIN sources AS item_source ON item_source.id = item.source_id
                  WHERE item.spec_id = s.id
                    AND item_source.ranking_permission = 'permitted'
                ),
                '[]'::jsonb
              ) AS maintenance_items
              ,COALESCE(
                (
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', rating.id,
                      'assessment_system', rating.assessment_system,
                      'assessment_year', rating.assessment_year,
                      'overall_stars', rating.overall_stars,
                      'adult_occupant_percent', rating.adult_occupant_percent,
                      'child_occupant_percent', rating.child_occupant_percent,
                      'vulnerable_road_users_percent', rating.vulnerable_road_users_percent,
                      'safety_assist_percent', rating.safety_assist_percent,
                      'source_id', rating.source_id,
                      'source_name', rating_source.name,
                      'source_url', rating.source_url,
                      'observed_at', rating.observed_at
                    ) ORDER BY rating.assessment_year DESC, rating.id
                  )
                  FROM vehicle_safety_ratings AS rating
                  JOIN sources AS rating_source ON rating_source.id = rating.source_id
                  WHERE rating.spec_id = s.id
                    AND rating_source.ranking_permission = 'permitted'
                ),
                '[]'::jsonb
              ) AS safety_ratings
              ,COALESCE(
                (
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', feature.id,
                      'feature_key', feature.feature_key,
                      'category', feature.category,
                      'name', feature.name,
                      'availability', feature.availability,
                      'notes', feature.notes,
                      'source_id', feature.source_id,
                      'source_name', feature_source.name,
                      'source_url', feature.source_url,
                      'observed_at', feature.observed_at
                    ) ORDER BY feature.feature_key, feature.id
                  )
                  FROM vehicle_features AS feature
                  JOIN sources AS feature_source ON feature_source.id = feature.source_id
                  WHERE feature.spec_id = s.id
                    AND feature.category IN ('adas', 'safety')
                    AND feature_source.ranking_permission = 'permitted'
                ),
                '[]'::jsonb
              ) AS safety_features
              ,COALESCE(
                (
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', feature.id,
                      'feature_key', feature.feature_key,
                      'category', feature.category,
                      'name', feature.name,
                      'availability', feature.availability,
                      'notes', feature.notes,
                      'source_id', feature.source_id,
                      'source_name', feature_source.name,
                      'source_url', feature.source_url,
                      'observed_at', feature.observed_at
                    ) ORDER BY feature.category, feature.feature_key, feature.id
                  )
                  FROM vehicle_features AS feature
                  JOIN sources AS feature_source ON feature_source.id = feature.source_id
                  WHERE feature.spec_id = s.id
                    AND feature.category IN ('technology', 'comfort')
                    AND feature_source.ranking_permission = 'permitted'
                ),
                '[]'::jsonb
              ) AS technology_comfort_features
"""

# One request-independent definition of an eligible offer. The offer query applies it
# to its own row; the list-price query asks that no such offer exists for the spec.
_ELIGIBLE_OFFER_GATES = """              AND upper(listing_source.market) = 'IT'
              AND listing_source.ranking_permission = 'permitted'
              AND l.is_active IS TRUE
              AND l.last_seen_at >= %s
              AND (l.valid_until IS NULL OR l.valid_until >= %s)
              AND nullif(trim(l.source_url), '') IS NOT NULL
              AND nullif(trim(listing_source.name), '') IS NOT NULL
              AND nullif(trim(listing_source.license), '') IS NOT NULL
              AND l.price_eur IS NOT NULL
              AND l.condition IN ('new', 'used', 'certified')
              AND (
                l.condition = 'new'
                OR l.mileage IS NOT NULL
              )
"""

_NO_ELIGIBLE_OFFER = """              AND NOT EXISTS (
                SELECT 1
                FROM listings AS l
                JOIN sources AS listing_source
                  ON listing_source.id = l.source_id
                JOIN import_runs AS import_run
                  ON import_run.id = l.import_run_id
                 AND import_run.status = 'completed'
                WHERE l.spec_id = s.id
                  AND l.vehicle_id = s.vehicle_id
""" + _ELIGIBLE_OFFER_GATES + """              )
"""

# Spec exclusion reasons shared by offers and list-price variants, in scoring order.
_SPEC_EXCLUSION_CASES = """                WHEN nullif(trim(s.body_style), '') IS NULL
                  THEN 'missing_body_style'
                WHEN nullif(trim(s.fuel_type), '') IS NULL
                  THEN 'missing_fuel_type'
                WHEN s.fuel_type NOT IN (
                  'diesel',
                  'electric',
                  'full_hybrid_petrol',
                  'hybrid_petrol',
                  'mild_hybrid_petrol',
                  'petrol',
                  'petrol_lpg',
                  'plug_in_hybrid_petrol'
                )
                  THEN 'unsupported_fuel_type'
                WHEN s.body_style NOT IN (
                  'city_car',
                  'crossover',
                  'hatchback',
                  'mpv',
                  'sedan',
                  'small_hatchback',
                  'suv',
                  'van',
                  'wagon'
                )
                  THEN 'unsupported_body_style'
                WHEN s.seats IS NULL
                  THEN 'missing_seats'
                WHEN s.cargo_volume_liters IS NULL
                  THEN 'missing_cargo'
                WHEN lower(s.fuel_type) = 'electric'
                  AND s.energy_consumption_kwh_100km IS NULL
                  THEN 'missing_ev_consumption'
                WHEN lower(s.fuel_type) = 'electric'
                  AND s.wltp_range_km IS NULL
                  THEN 'missing_ev_range'
                WHEN lower(s.fuel_type) <> 'electric'
                  AND lower(s.fuel_type) <> 'plug_in_hybrid_petrol'
                  AND s.consumption_l_100km IS NULL
                  THEN 'missing_liquid_consumption'
                WHEN EXISTS (
                  SELECT 1
                  FROM (
                    VALUES
                      ('body_style'),
                      ('fuel_type'),
                      ('seats'),
                      ('cargo_volume_liters')
                  ) AS required_metric(metric)
                  WHERE NOT EXISTS (
                    SELECT 1
                    FROM catalog_read_provenance AS required_provenance
                    JOIN sources AS required_provenance_source
                      ON required_provenance_source.id = required_provenance.source_id
                    WHERE required_provenance.spec_id = s.id
                      AND required_provenance.is_current
                      AND required_provenance_source.ranking_permission = 'permitted'
                      AND COALESCE(
                        required_provenance.metadata->'supported_metrics',
                        required_provenance.metadata->'metrics',
                        '[]'::jsonb
                      ) ? required_metric.metric
                  )
                ) OR (
                  s.fuel_type = 'electric'
                  AND (
                    NOT EXISTS (
                      SELECT 1
                      FROM catalog_read_provenance AS energy_provenance
                      JOIN sources AS energy_provenance_source
                        ON energy_provenance_source.id = energy_provenance.source_id
                      WHERE energy_provenance.spec_id = s.id
                        AND energy_provenance.is_current
                        AND energy_provenance_source.ranking_permission = 'permitted'
                        AND COALESCE(
                          energy_provenance.metadata->'supported_metrics',
                          energy_provenance.metadata->'metrics',
                          '[]'::jsonb
                        ) ? 'energy_consumption_kwh_100km'
                    )
                    OR NOT EXISTS (
                      SELECT 1
                      FROM catalog_read_provenance AS range_provenance
                      JOIN sources AS range_provenance_source
                        ON range_provenance_source.id = range_provenance.source_id
                      WHERE range_provenance.spec_id = s.id
                        AND range_provenance.is_current
                        AND range_provenance_source.ranking_permission = 'permitted'
                        AND COALESCE(
                          range_provenance.metadata->'supported_metrics',
                          range_provenance.metadata->'metrics',
                          '[]'::jsonb
                        ) ? 'wltp_range_km'
                    )
                  )
                ) OR (
                  s.fuel_type <> 'electric'
                  AND s.fuel_type <> 'plug_in_hybrid_petrol'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM catalog_read_provenance AS liquid_provenance
                    JOIN sources AS liquid_provenance_source
                      ON liquid_provenance_source.id = liquid_provenance.source_id
                    WHERE liquid_provenance.spec_id = s.id
                      AND liquid_provenance.is_current
                      AND liquid_provenance_source.ranking_permission = 'permitted'
                      AND COALESCE(
                        liquid_provenance.metadata->'supported_metrics',
                        liquid_provenance.metadata->'metrics',
                        '[]'::jsonb
                      ) ? 'consumption_l_100km'
                  )
                )
                  THEN 'missing_spec_provenance'
"""

# Spec gates shared by offer and list-price candidates: permitted provenance first,
# then the values the car module scores.
_SPEC_PROVENANCE_GATES = """              AND nullif(trim(v.model_family_key), '') IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM (
                  VALUES
                    ('body_style'),
                    ('fuel_type'),
                    ('seats'),
                    ('cargo_volume_liters')
                ) AS required_metric(metric)
                WHERE NOT EXISTS (
                  SELECT 1
                  FROM catalog_read_provenance AS required_provenance
                  JOIN sources AS required_provenance_source
                    ON required_provenance_source.id = required_provenance.source_id
                  WHERE required_provenance.spec_id = s.id
                    AND required_provenance.is_current
                    AND required_provenance_source.ranking_permission = 'permitted'
                    AND COALESCE(
                      required_provenance.metadata->'supported_metrics',
                      required_provenance.metadata->'metrics',
                      '[]'::jsonb
                    ) ? required_metric.metric
                )
              )
              AND (
                (
                  s.fuel_type = 'electric'
                  AND EXISTS (
                    SELECT 1
                    FROM catalog_read_provenance AS energy_provenance
                    JOIN sources AS energy_provenance_source
                      ON energy_provenance_source.id = energy_provenance.source_id
                    WHERE energy_provenance.spec_id = s.id
                      AND energy_provenance.is_current
                      AND energy_provenance_source.ranking_permission = 'permitted'
                      AND COALESCE(
                        energy_provenance.metadata->'supported_metrics',
                        energy_provenance.metadata->'metrics',
                        '[]'::jsonb
                      ) ? 'energy_consumption_kwh_100km'
                  )
                  AND EXISTS (
                    SELECT 1
                    FROM catalog_read_provenance AS range_provenance
                    JOIN sources AS range_provenance_source
                      ON range_provenance_source.id = range_provenance.source_id
                    WHERE range_provenance.spec_id = s.id
                      AND range_provenance.is_current
                      AND range_provenance_source.ranking_permission = 'permitted'
                      AND COALESCE(
                        range_provenance.metadata->'supported_metrics',
                        range_provenance.metadata->'metrics',
                        '[]'::jsonb
                      ) ? 'wltp_range_km'
                  )
                )
                OR s.fuel_type = 'plug_in_hybrid_petrol'
                OR (
                  s.fuel_type <> 'electric'
                  AND s.fuel_type <> 'plug_in_hybrid_petrol'
                  AND EXISTS (
                    SELECT 1
                    FROM catalog_read_provenance AS liquid_provenance
                    JOIN sources AS liquid_provenance_source
                      ON liquid_provenance_source.id = liquid_provenance.source_id
                    WHERE liquid_provenance.spec_id = s.id
                      AND liquid_provenance.is_current
                      AND liquid_provenance_source.ranking_permission = 'permitted'
                      AND COALESCE(
                        liquid_provenance.metadata->'supported_metrics',
                        liquid_provenance.metadata->'metrics',
                        '[]'::jsonb
                      ) ? 'consumption_l_100km'
                  )
                )
              )
"""

_SPEC_VALUE_GATES = """              AND nullif(trim(s.variant_key), '') IS NOT NULL
              AND nullif(trim(s.body_style), '') IS NOT NULL
              AND nullif(trim(s.fuel_type), '') IS NOT NULL
              AND s.fuel_type IN (
                'diesel',
                'electric',
                'full_hybrid_petrol',
                'hybrid_petrol',
                'mild_hybrid_petrol',
                'petrol',
                'petrol_lpg',
                'plug_in_hybrid_petrol'
              )
              AND s.body_style IN (
                'city_car',
                'crossover',
                'hatchback',
                'mpv',
                'sedan',
                'small_hatchback',
                'suv',
                'van',
                'wagon'
              )
              AND s.seats IS NOT NULL
              AND s.cargo_volume_liters IS NOT NULL
              AND (
                (
                  lower(s.fuel_type) = 'electric'
                  AND s.energy_consumption_kwh_100km IS NOT NULL
                  AND s.wltp_range_km IS NOT NULL
                )
                OR lower(s.fuel_type) = 'plug_in_hybrid_petrol'
                OR (
                  lower(s.fuel_type) <> 'electric'
                  AND lower(s.fuel_type) <> 'plug_in_hybrid_petrol'
                  AND s.consumption_l_100km IS NOT NULL
                )
              )
"""


class AdvisorRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    def list_candidates(
        self,
        *,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Offer candidates, then variants with no eligible offer at list price (ADR-013)."""
        evaluation_time = _as_utc(as_of)
        fresh_since = evaluation_time - timedelta(days=FRESHNESS_DAYS)
        rows = self.conn.execute(
            _CANDIDATE_SPEC_COLUMNS
            + _CANDIDATE_LISTING_COLUMNS
            + _CANDIDATE_CHILDREN
            + """            FROM listings AS l
            JOIN vehicles AS v
              ON v.id = l.vehicle_id
            JOIN catalog_read_specs AS s
              ON s.id = l.spec_id
             AND s.vehicle_id = l.vehicle_id
            JOIN sources AS listing_source
              ON listing_source.id = l.source_id
            JOIN import_runs AS import_run
              ON import_run.id = l.import_run_id
             AND import_run.status = 'completed'
            WHERE upper(v.market) = 'IT'
              AND """
            + CAR_ONLY_SQL
            + "\n"
            + _ELIGIBLE_OFFER_GATES
            + _SPEC_PROVENANCE_GATES
            + _SPEC_VALUE_GATES
            + """            ORDER BY
              l.condition,
              v.model_family_key,
              l.price_eur,
              l.mileage NULLS LAST,
              l.listing_ref,
              l.id
            """,
            (fresh_since, evaluation_time),
        ).fetchall()
        candidates = [_candidate_from_row(row) for row in rows]
        list_price_rows = self.conn.execute(
            _CANDIDATE_SPEC_COLUMNS
            + LIST_PRICE_COLUMNS
            + _CANDIDATE_CHILDREN
            + """            FROM vehicles AS v
            JOIN catalog_read_specs AS s
              ON s.vehicle_id = v.id
            """
            + LIST_PRICE_FACT_JOIN
            + """            WHERE upper(v.market) = 'IT'
              AND s.catalog_version = 2
              AND """
            + CAR_ONLY_SQL
            + "\n"
            + _NO_ELIGIBLE_OFFER
            + """              AND s.list_price_eur IS NOT NULL
              AND list_price.decision_id IS NOT NULL
              AND list_price.source_url LIKE 'https://%%'
"""
            + _SPEC_PROVENANCE_GATES
            + _SPEC_VALUE_GATES
            + """            ORDER BY
              v.model_family_key,
              s.list_price_eur,
              s.variant_key,
              s.id
            """,
            (fresh_since, evaluation_time),
        ).fetchall()
        candidates.extend(_list_price_candidate_from_row(row) for row in list_price_rows)
        return candidates

    def count_excluded_candidates(
        self,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, int]:
        evaluation_time = _as_utc(as_of)
        fresh_since = evaluation_time - timedelta(days=FRESHNESS_DAYS)
        rows = self.conn.execute(
            """
            WITH classified AS (
              SELECT CASE
                WHEN NOT """ + CAR_ONLY_SQL + """
                  THEN 'unsupported_vehicle_type'
                WHEN upper(v.market) <> 'IT'
                  OR upper(listing_source.market) <> 'IT'
                  THEN 'non_it_market'
                WHEN listing_source.ranking_permission <> 'permitted'
                  THEN 'source_not_permitted'
                WHEN l.is_active IS NOT TRUE
                  THEN 'inactive_offer'
                WHEN l.last_seen_at IS NULL OR l.last_seen_at < %s
                  THEN 'stale_offer'
                WHEN l.valid_until IS NOT NULL AND l.valid_until < %s
                  THEN 'expired_offer'
                WHEN nullif(trim(l.source_url), '') IS NULL
                  OR nullif(trim(listing_source.name), '') IS NULL
                  OR nullif(trim(listing_source.license), '') IS NULL
                  OR import_run.status IS DISTINCT FROM 'completed'
                  THEN 'unreviewed_source'
                WHEN l.spec_id IS NULL OR s.id IS NULL
                  OR s.vehicle_id IS DISTINCT FROM l.vehicle_id
                  OR nullif(trim(s.variant_key), '') IS NULL
                  THEN 'unresolved_spec'
                WHEN nullif(trim(v.model_family_key), '') IS NULL
                  THEN 'missing_model_family_key'
                WHEN l.price_eur IS NULL
                  THEN 'missing_price'
                WHEN l.condition NOT IN ('new', 'used', 'certified')
                  THEN 'invalid_condition'
                WHEN l.condition IN ('used', 'certified') AND l.mileage IS NULL
                  THEN 'missing_mileage'
""" + _SPEC_EXCLUSION_CASES + """                ELSE NULL
              END AS reason
              FROM listings AS l
              JOIN vehicles AS v
                ON v.id = l.vehicle_id
              JOIN sources AS listing_source
                ON listing_source.id = l.source_id
              LEFT JOIN catalog_read_specs AS s
                ON s.id = l.spec_id
               AND s.vehicle_id = l.vehicle_id
              LEFT JOIN import_runs AS import_run
                ON import_run.id = l.import_run_id
            )
            SELECT reason, count(*)::integer AS excluded_count
            FROM classified
            WHERE reason IS NOT NULL
            GROUP BY reason
            ORDER BY reason
            """,
            (fresh_since, evaluation_time),
        ).fetchall()
        counts = {row["reason"]: row["excluded_count"] for row in rows}
        for row in self.conn.execute(
            """
            WITH classified AS (
              SELECT CASE
                WHEN s.list_price_eur IS NULL AND EXISTS (
                  SELECT 1 FROM catalog_current_facts AS fact
                  WHERE fact.spec_id = s.id
                    AND fact.metric = 'list_price_eur'
                    AND fact.status = 'verified'
                    AND NOT fact.eligible
                )
                  THEN 'source_not_permitted'
                WHEN s.list_price_eur IS NULL
                  OR list_price.decision_id IS NULL
                  OR list_price.source_url NOT LIKE 'https://%%'
                  THEN 'missing_list_price'
                WHEN nullif(trim(s.variant_key), '') IS NULL
                  THEN 'unresolved_spec'
                WHEN nullif(trim(v.model_family_key), '') IS NULL
                  THEN 'missing_model_family_key'
"""
            + _SPEC_EXCLUSION_CASES
            + """                ELSE NULL
              END AS reason
              FROM vehicles AS v
              JOIN catalog_read_specs AS s
                ON s.vehicle_id = v.id
              """
            + LIST_PRICE_FACT_JOIN
            + """              WHERE upper(v.market) = 'IT'
                AND s.catalog_version = 2
                AND """
            + CAR_ONLY_SQL
            + "\n"
            + _NO_ELIGIBLE_OFFER
            + """            )
            SELECT reason, count(*)::integer AS excluded_count
            FROM classified
            WHERE reason IS NOT NULL
            GROUP BY reason
            ORDER BY reason
            """,
            (fresh_since, evaluation_time),
        ).fetchall():
            counts[row["reason"]] = counts.get(row["reason"], 0) + row["excluded_count"]
        return counts

    def list_model_analysis_candidates(self) -> list[dict[str, Any]]:
        evaluation_time = datetime.now(timezone.utc)
        rows = self.conn.execute(
            """
            SELECT
              v.id AS vehicle_id,
              v.canonical_key,
              v.model_family_key,
              v.make,
              v.model,
              v.model_year,
              v.catalog_version, v.vehicle_type, v.generation_key, v.phase_key,
              s.body_style AS vehicle_body_style,
              s.fuel_type AS vehicle_fuel_type,
              v.market,
              NULL::numeric AS base_price_eur,
              s.id AS spec_id,
              s.variant_key,
              s.catalog_version AS spec_catalog_version,
              s.powertrain_type,
              s.fuel,
              s.engine_code,
              s.valid_from,
              s.valid_to,
              s.external_references,
              s.is_default,
              s.trim,
              s.body_style AS spec_body_style,
              s.fuel_type AS spec_fuel_type,
              s.list_price_eur,
              s.drivetrain,
              s.transmission,
              s.engine,
              s.horsepower,
              s.battery_kwh,
              s.energy_consumption_kwh_100km,
              s.consumption_l_100km,
              s.consumption_l_100km_basis,
              s.energy_consumption_kwh_100km_basis,
              s.wltp_range_km,
              s.co2_g_km,
              s.euro_emission_standard,
              s.seats,
              s.cargo_volume_liters,
"""
            + LIST_PRICE_COLUMNS
            + """              l.id AS listing_id,
              l.source_id,
              l.listing_ref,
              l.title,
              l.price_eur,
              l.mileage,
              l.condition,
              l.location_region,
              l.source_url,
              l.listed_at,
              l.last_seen_at,
              l.valid_until,
              l.is_active
            FROM vehicles AS v
            LEFT JOIN catalog_analysis_specs AS s
              ON s.vehicle_id = v.id
            """
            + LIST_PRICE_FACT_JOIN
            + """            LEFT JOIN catalog_usable_listings AS l
              ON l.vehicle_id = v.id
             AND l.spec_id = s.id
             AND l.last_seen_at >= %s
             AND (l.valid_until IS NULL OR l.valid_until >= %s)
            WHERE """ + CAR_ONLY_SQL + """
            ORDER BY
              v.make,
              v.model,
              v.model_year,
              s.is_default DESC NULLS LAST,
              s.variant_key NULLS LAST,
              s.id,
              l.price_eur NULLS LAST,
              l.id
            """,
            (evaluation_time - timedelta(days=FRESHNESS_DAYS), evaluation_time),
        ).fetchall()
        grouped: dict[UUID, dict[str, Any]] = {}
        seen_specs: set[UUID] = set()
        seen_listings: set[UUID] = set()
        for row in rows:
            vehicle_id = row["vehicle_id"]
            candidate = grouped.setdefault(
                vehicle_id,
                {
                    "vehicle": _model_analysis_vehicle(row),
                    "specs": [],
                    "listings": [],
                },
            )
            spec_id = row["spec_id"]
            if spec_id is not None and spec_id not in seen_specs:
                candidate["specs"].append(_model_analysis_spec(row))
                seen_specs.add(spec_id)
            listing_id = row["listing_id"]
            if listing_id is not None and listing_id not in seen_listings:
                candidate["listings"].append(_model_analysis_listing(row))
                seen_listings.add(listing_id)
        return list(grouped.values())

    def create_run(
        self,
        request_payload: dict[str, Any],
        *,
        scoring_version: str = SCORING_VERSION,
        assumptions: list[str] | None = None,
        exclusion_counts: dict[str, int] | None = None,
    ) -> UUID:
        run_id = uuid4()
        self.conn.execute(
            """
            INSERT INTO recommendation_runs (
              id,
              request_payload,
              status,
              scoring_version,
              assumptions,
              exclusion_counts
            )
            VALUES (%s, %s, 'queued', %s, %s, %s)
            """,
            (
                run_id,
                Jsonb(request_payload),
                scoring_version,
                Jsonb(assumptions or []),
                Jsonb(exclusion_counts or {}),
            ),
        )
        return run_id

    def save_items(
        self,
        run_id: UUID,
        groups_or_items: list[AdvisorRecommendationGroup]
        | list[AdvisorRecommendationItem],
    ) -> None:
        ranked_items = _ranked_items(groups_or_items)
        for condition_group, rank, item in ranked_items:
            breakdown = {
                "condition_group": condition_group,
                "decision_status": item.decision_status,
                "decision_score": item.decision_score,
                "decision_confidence": item.decision_confidence,
                "confidence_components": {
                    key: item.evidence.get(key)
                    for key in (
                        "profile_completeness",
                        "evidence_completeness",
                        "ranking_stability",
                        "ranking_comparison",
                    )
                    if key in item.evidence
                },
                "structural_fit": item.structural_fit,
                "preference_fit": item.preference_fit,
                "pillar_scores": item.pillar_scores,
                "penalties": item.penalties,
                "missing_factors": item.missing_factors,
                "warnings": item.warnings,
                "module_versions": item.module_versions,
                "assumptions": item.assumptions,
                "strengths": item.strengths,
                "score_composition": item.score_composition,
                "component_scores": item.component_scores,
                "positive_factors": [
                    factor.model_dump(mode="json") for factor in item.positive_factors
                ],
                "tradeoffs": [
                    factor.model_dump(mode="json") for factor in item.tradeoffs
                ],
                "evidence": item.evidence,
                "price_basis": item.price_basis,
                "list_price": (
                    item.list_price.model_dump(mode="json") if item.list_price else None
                ),
                "provenance": [
                    entry.model_dump(mode="json") for entry in item.provenance
                ],
            }
            if "normalized_weights" in item.evidence:
                breakdown["legacy_compatibility"] = {
                    "label": "v2_normalized_weights",
                    "normalized_weights": item.evidence["normalized_weights"],
                }
            rationale = " ".join(
                factor.message
                for factor in [*item.positive_factors, *item.tradeoffs]
            )
            self.conn.execute(
                """
                INSERT INTO recommendation_items (
                  id,
                  run_id,
                  vehicle_id,
                  listing_id,
                  spec_id,
                  condition_group,
                  rank,
                  score,
                  rationale,
                  scoring_version,
                  score_breakdown
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    run_id,
                    item.vehicle.id,
                    item.offer.id if item.offer else None,
                    item.selected_spec.id,
                    condition_group,
                    rank,
                    item.score,
                    rationale,
                    SCORING_VERSION,
                    Jsonb(breakdown),
                ),
            )

    def mark_run_completed(self, run_id: UUID) -> None:
        self.conn.execute(
            """
            UPDATE recommendation_runs
            SET status = 'completed',
                completed_at = now()
            WHERE id = %s
            """,
            (run_id,),
        )


def _candidate_from_row(row: dict[str, Any]) -> dict[str, Any]:
    trusted_dimensions = {
        metric: _trusted_metric(row, metric, row[column])
        for metric, column in (
            ("length_mm", "length_mm"),
            ("width_mm", "width_mm"),
            ("height_mm", "height_mm"),
            ("curb_weight_kg", "curb_weight_kg"),
            ("power_kw", "power_kw"),
        )
    }
    spec = {
        "id": row["spec_id"],
        "variant_key": row["variant_key"],
        "catalog_version": row.get("spec_catalog_version", 1),
        "powertrain_type": row.get("powertrain_type"),
        "fuel": row.get("fuel"),
        "engine_code": row.get("engine_code"),
        "valid_from": row.get("valid_from"),
        "valid_to": row.get("valid_to"),
        "external_references": row.get("external_references") or [],
        "is_default": row["is_default"],
        "trim": row["trim"],
        "body_style": row["spec_body_style"],
        "fuel_type": row["spec_fuel_type"],
        "list_price_eur": row["list_price_eur"],
        "drivetrain": row["drivetrain"],
        "transmission": row["transmission"],
        "transmission_type": _trusted_metric(row, "transmission_type", row.get("transmission_type")),
        "engine": row["engine"],
        "horsepower": row["horsepower"],
        "battery_kwh": row["battery_kwh"],
        "energy_consumption_kwh_100km": row[
            "energy_consumption_kwh_100km"
        ],
        "consumption_l_100km": row["consumption_l_100km"],
        "consumption_l_100km_basis": row.get("consumption_l_100km_basis"),
        "energy_consumption_kwh_100km_basis": row.get(
            "energy_consumption_kwh_100km_basis"
        ),
        "wltp_range_km": row["wltp_range_km"],
        "co2_g_km": row["co2_g_km"],
        "euro_emission_standard": row["euro_emission_standard"],
        "seats": row["seats"],
        "cargo_volume_liters": row["cargo_volume_liters"],
        "length_mm": trusted_dimensions["length_mm"],
        "width_mm": trusted_dimensions["width_mm"],
        "height_mm": trusted_dimensions["height_mm"],
        "curb_weight_kg": trusted_dimensions["curb_weight_kg"],
        "power_kw": trusted_dimensions["power_kw"],
    }
    offer = {
        "id": row["listing_id"],
        "vehicle_id": row["vehicle_id"],
        "spec_id": row["spec_id"],
        "source_id": row["source_id"],
        "listing_ref": row["listing_ref"],
        "title": row["title"],
        "price_eur": row["price_eur"],
        "mileage": row["mileage"],
        "condition": row["condition"],
        "location_region": row["location_region"],
        "source_url": row["source_url"],
        "listed_at": row["listed_at"],
        "last_seen_at": row["last_seen_at"],
        "valid_until": row["valid_until"],
        "is_active": row["is_active"],
    }
    candidate = {
        "vehicle": _model_analysis_vehicle(row),
        "spec": spec,
        "offer": offer,
        "source": {
            "name": row["listing_source_name"],
            "license": row["listing_source_license"],
            "ranking_permission": row["listing_source_ranking_permission"],
        },
        "import_status": row["import_status"],
        "price_basis": "offer",
        "reviewed": True,
        "repository_eligible": True,
        "provenance": _offer_provenance(row, offer) + _metric_provenance(row, spec),
    }
    candidate["decision_context"] = {
        "identity": {
            "generation_name": row["generation_name"],
            "restyling_label": row["restyling_label"],
            "category": row["category"],
        },
        "dimensions": {
            "length_mm": trusted_dimensions["length_mm"],
            "body_width_mm": trusted_dimensions["width_mm"],
            "height_mm": trusted_dimensions["height_mm"],
            "width_mirrors_folded_mm": None,
            "curb_weight_kg": trusted_dimensions["curb_weight_kg"],
        },
        "powertrain": {
            "engine_code": row["engine_code"],
            "power_kw": trusted_dimensions["power_kw"],
            "fuel_type": row["spec_fuel_type"],
            "transmission_type": spec["transmission_type"],
        },
        "performance": {
            "acceleration_0_100_s": row["acceleration_0_100_s"],
            "top_speed_kmh": row["top_speed_kmh"],
            "braking_100_0_m": row["braking_100_0_m"],
        },
        "maintenance": row["maintenance_items"] or [],
        "safety": {
            "ratings": row["safety_ratings"] or [],
            "features": row["safety_features"] or [],
        },
        "technology_comfort": row["technology_comfort_features"] or [],
    }
    return candidate


def _model_analysis_vehicle(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["vehicle_id"],
        "canonical_key": row["canonical_key"],
        "model_family_key": row["model_family_key"],
        "make": row["make"],
        "model": row["model"],
        "model_year": row["model_year"],
        "catalog_version": row.get("catalog_version", 1),
        "vehicle_type": row.get("vehicle_type"),
        "generation_key": row.get("generation_key"),
        "phase_key": row.get("phase_key"),
        "body_style": row["vehicle_body_style"],
        "fuel_type": row["vehicle_fuel_type"],
        "market": row["market"],
        "base_price_eur": row["base_price_eur"],
    }


def _model_analysis_spec(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["spec_id"],
        "variant_key": row["variant_key"],
        "catalog_version": row.get("spec_catalog_version", 1),
        "powertrain_type": row.get("powertrain_type"),
        "fuel": row.get("fuel"),
        "engine_code": row.get("engine_code"),
        "valid_from": row.get("valid_from"),
        "valid_to": row.get("valid_to"),
        "external_references": row.get("external_references") or [],
        "is_default": row["is_default"],
        "trim": row["trim"],
        "body_style": row["spec_body_style"],
        "fuel_type": row["spec_fuel_type"],
        "list_price_eur": row["list_price_eur"],
        "drivetrain": row["drivetrain"],
        "transmission": row["transmission"],
        "engine": row["engine"],
        "horsepower": row["horsepower"],
        "battery_kwh": row["battery_kwh"],
        "energy_consumption_kwh_100km": row[
            "energy_consumption_kwh_100km"
        ],
        "consumption_l_100km": row["consumption_l_100km"],
        "consumption_l_100km_basis": row.get("consumption_l_100km_basis"),
        "energy_consumption_kwh_100km_basis": row.get(
            "energy_consumption_kwh_100km_basis"
        ),
        "wltp_range_km": row["wltp_range_km"],
        "co2_g_km": row["co2_g_km"],
        "euro_emission_standard": row["euro_emission_standard"],
        "seats": row["seats"],
        "cargo_volume_liters": row["cargo_volume_liters"],
        # The source and terms of list_price_eur, under the Advisor URL rule.
        "list_price": (
            list_price_block(row)
            if row.get("list_price_decision_id") is not None
            and str(row.get("list_price_source_url") or "").startswith("https://")
            else None
        ),
    }


def _model_analysis_listing(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["listing_id"],
        "vehicle_id": row["vehicle_id"],
        "spec_id": row["spec_id"],
        "source_id": row["source_id"],
        "listing_ref": row["listing_ref"],
        "title": row["title"],
        "price_eur": row["price_eur"],
        "mileage": row["mileage"],
        "condition": row["condition"],
        "location_region": row["location_region"],
        "source_url": row["source_url"],
        "listed_at": row["listed_at"],
        "last_seen_at": row["last_seen_at"],
        "valid_until": row["valid_until"],
        "is_active": row["is_active"],
    }


_LISTING_ROW_KEYS = (
    "listing_id",
    "source_id",
    "listing_ref",
    "title",
    "price_eur",
    "mileage",
    "condition",
    "location_region",
    "source_url",
    "listed_at",
    "last_seen_at",
    "valid_until",
    "is_active",
    "listing_source_name",
    "listing_source_license",
    "listing_source_ranking_permission",
    "import_status",
)


def _list_price_candidate_from_row(row: dict[str, Any]) -> dict[str, Any]:
    """A variant with no eligible offer, evaluated as new at its list price (ADR-013)."""
    # The list-price query has no listing columns; the shared mapper sees them as empty.
    candidate = _candidate_from_row({**dict.fromkeys(_LISTING_ROW_KEYS), **row})
    candidate.update(
        offer=None,
        source=None,
        import_status=None,
        price_basis="list_price",
        list_price=list_price_block(row),
    )
    candidate["provenance"] = [
        {
            "metric": "list_price_eur",
            "source_name": row.get("list_price_source_name"),
            "source_url": row.get("list_price_source_url"),
            "source_license": row.get("list_price_source_license"),
            "observed_at": row.get("list_price_observed_at"),
            "decision_id": row.get("list_price_decision_id"),
            "observation_id": row.get("list_price_observation_id"),
        },
        *_metric_provenance(row, candidate["spec"]),
    ]
    return candidate


def _offer_provenance(
    row: dict[str, Any],
    offer: dict[str, Any],
) -> list[dict[str, Any]]:
    provenance = [
        {
            "metric": "price_eur",
            "source_name": row["listing_source_name"],
            "source_url": offer["source_url"],
            "source_license": row["listing_source_license"],
            "observed_at": offer["last_seen_at"],
        }
    ]
    if offer["mileage"] is not None:
        provenance.append(
            {
                "metric": "mileage",
                "source_name": row["listing_source_name"],
                "source_url": offer["source_url"],
                "source_license": row["listing_source_license"],
                "observed_at": offer["last_seen_at"],
            }
        )
    return provenance


def _metric_provenance(
    row: dict[str, Any],
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    provenance: list[dict[str, Any]] = []
    technical_metrics = (
        "body_style",
        "fuel_type",
        "seats",
        "cargo_volume_liters",
        "consumption_l_100km",
        "energy_consumption_kwh_100km",
        "wltp_range_km",
        "length_mm",
        "width_mm",
        "height_mm",
        "curb_weight_kg",
        "power_kw",
        "transmission_type",
    )
    for source in row["spec_provenance"] or []:
        metadata = source.get("metadata") or {}
        supported_metrics = set(
            metadata.get("supported_metrics") or metadata.get("metrics") or []
        )
        for metric in technical_metrics:
            if metric not in supported_metrics or spec.get(metric) is None:
                continue
            provenance.append(
                {
                    "metric": metric,
                    "source_name": source["source_name"],
                    "source_url": source["source_url"],
                    "source_license": source.get("source_license"),
                    "observed_at": source["observed_at"],
                    "decision_id": metadata.get("decision_id"),
                    "observation_id": metadata.get("observation_id"),
                }
            )
    return provenance


def _trusted_metric(
    row: dict[str, Any],
    metric: str,
    value: Any,
) -> Any:
    if value is None:
        return None
    for source in row.get("spec_provenance") or []:
        source_url = source.get("source_url")
        metadata = source.get("metadata") or {}
        supported_metrics = set(
            metadata.get("supported_metrics") or metadata.get("metrics") or []
        )
        if metric in supported_metrics and isinstance(source_url, str) and source_url.startswith("https://"):
            return value
    return None


def _ranked_items(
    groups_or_items: list[AdvisorRecommendationGroup]
    | list[AdvisorRecommendationItem],
) -> list[tuple[str, int, AdvisorRecommendationItem]]:
    if not groups_or_items:
        return []
    first = groups_or_items[0]
    if isinstance(first, AdvisorRecommendationGroup):
        return [
            (group.condition, rank, item)
            for group in groups_or_items
            if isinstance(group, AdvisorRecommendationGroup)
            for rank, item in enumerate(group.items, start=1)
        ]
    counters = {"new": 0, "used": 0}
    ranked: list[tuple[str, int, AdvisorRecommendationItem]] = []
    for item in groups_or_items:
        if not isinstance(item, AdvisorRecommendationItem):
            continue
        condition_group = item.condition_group
        counters[condition_group] += 1
        ranked.append((condition_group, counters[condition_group], item))
    return ranked


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
