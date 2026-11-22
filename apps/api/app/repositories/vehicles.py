from typing import Any
from uuid import UUID

from app.repositories.filters import VehicleFilters


PROFILE_PROVENANCE_FIELDS = (
    "source_id",
    "source_key",
    "source_name",
    "source_url",
    "source_license",
    "observed_at",
)


def _profile_provenance(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row[field] for field in PROFILE_PROVENANCE_FIELDS}


def _group_by_spec_id(rows: list[dict[str, Any]]) -> dict[UUID, list[dict[str, Any]]]:
    grouped: dict[UUID, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["spec_id"], []).append(row)
    return grouped


def _feature_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "feature_key": row["feature_key"],
        "category": row["category"],
        "name": row["name"],
        "availability": row["availability"],
        "notes": row["notes"],
        "provenance": _profile_provenance(row),
    }


class VehiclesRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    def list_vehicles(self, filters: VehicleFilters) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        variant_clauses: list[str] = []
        params: list[object] = []

        if filters.make:
            where_clauses.append("v.make ILIKE %s")
            params.append(f"%{filters.make}%")
        if filters.model:
            where_clauses.append("v.model ILIKE %s")
            params.append(f"%{filters.model}%")
        if filters.fuel_type:
            variant_clauses.append("candidate.fuel_type = %s")
            params.append(filters.fuel_type)
        if filters.body_style:
            variant_clauses.append("candidate.body_style = %s")
            params.append(filters.body_style)
        if filters.max_price_eur is not None:
            variant_clauses.append("candidate.list_price_eur <= %s")
            params.append(filters.max_price_eur)
        if variant_clauses:
            where_clauses.append(
                "EXISTS ("
                "SELECT 1 FROM vehicle_specs candidate "
                "WHERE candidate.vehicle_id = v.id AND "
                + " AND ".join(variant_clauses)
                + ")"
            )
        if filters.market:
            where_clauses.append("v.market = %s")
            params.append(filters.market)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT
              v.id,
              v.canonical_key,
              v.model_family_key,
              v.make,
              v.model,
              v.model_year,
              COALESCE(default_spec.body_style, v.body_style) AS body_style,
              COALESCE(default_spec.fuel_type, v.fuel_type) AS fuel_type,
              v.market,
              COALESCE(default_spec.list_price_eur, v.base_price_eur) AS base_price_eur
            FROM vehicles v
            LEFT JOIN vehicle_specs default_spec
              ON default_spec.vehicle_id = v.id AND default_spec.is_default
            {where_sql}
            ORDER BY v.make, v.model, v.model_year
            LIMIT %s OFFSET %s
        """

        params.extend([filters.limit, filters.offset])
        return list(self.conn.execute(query, params).fetchall())

    def get_vehicle(self, vehicle_id: UUID) -> dict[str, Any] | None:
        vehicle = self.conn.execute(
            """
            SELECT
              v.id,
              v.canonical_key,
              v.model_family_key,
              v.make,
              v.model,
              v.model_year,
              COALESCE(s.body_style, v.body_style) AS body_style,
              COALESCE(s.fuel_type, v.fuel_type) AS fuel_type,
              v.market,
              COALESCE(s.list_price_eur, v.base_price_eur) AS base_price_eur
            FROM vehicles v
            LEFT JOIN vehicle_specs s
              ON s.vehicle_id = v.id AND s.is_default
            WHERE v.id = %s
            """,
            (vehicle_id,),
        ).fetchone()

        if vehicle is None:
            return None

        specs = self.conn.execute(
            """
            SELECT
              id,
              variant_key,
              is_default,
              trim,
              body_style,
              fuel_type,
              list_price_eur,
              drivetrain,
              transmission,
              engine,
              horsepower,
              battery_kwh,
              energy_consumption_kwh_100km,
              consumption_l_100km,
              wltp_range_km,
              co2_g_km,
              euro_emission_standard,
              seats,
              cargo_volume_liters,
              generation_name,
              restyling_label,
              category,
              doors,
              length_mm,
              width_mm,
              height_mm,
              wheelbase_mm,
              curb_weight_kg,
              gross_weight_kg,
              payload_kg,
              engine_code,
              displacement_cc,
              cylinders,
              power_kw,
              torque_nm,
              battery_usable_kwh,
              transmission_type,
              gear_count,
              differential_type,
              acceleration_0_100_s,
              top_speed_kmh,
              braking_100_0_m,
              homologation_cycle
            FROM vehicle_specs
            WHERE vehicle_id = %s
            ORDER BY is_default DESC, trim, variant_key
            """,
            (vehicle_id,),
        ).fetchall()

        spec_ids = [spec["id"] for spec in specs]
        maintenance_by_spec = _group_by_spec_id(
            list(
                self.conn.execute(
                    """
                    SELECT
                      child.spec_id,
                      child.id,
                      child.operation_code,
                      child.title,
                      child.interval_km,
                      child.interval_months,
                      child.notes,
                      child.source_id,
                      source.source_key,
                      source.name AS source_name,
                      child.source_url,
                      source.license AS source_license,
                      child.observed_at
                    FROM vehicle_maintenance_items child
                    JOIN sources source ON source.id = child.source_id
                    WHERE child.spec_id = ANY(%s)
                    ORDER BY child.spec_id, child.created_at, child.id
                    """,
                    (spec_ids,),
                ).fetchall()
            )
        )
        safety_ratings_by_spec = _group_by_spec_id(
            list(
                self.conn.execute(
                    """
                    SELECT
                      child.spec_id,
                      child.id,
                      child.assessment_system,
                      child.assessment_year,
                      child.overall_stars,
                      child.adult_occupant_percent,
                      child.child_occupant_percent,
                      child.vulnerable_road_users_percent,
                      child.safety_assist_percent,
                      child.source_id,
                      source.source_key,
                      source.name AS source_name,
                      child.source_url,
                      source.license AS source_license,
                      child.observed_at
                    FROM vehicle_safety_ratings child
                    JOIN sources source ON source.id = child.source_id
                    WHERE child.spec_id = ANY(%s)
                    ORDER BY child.spec_id, child.created_at, child.id
                    """,
                    (spec_ids,),
                ).fetchall()
            )
        )
        features_by_spec = _group_by_spec_id(
            list(
                self.conn.execute(
                    """
                    SELECT
                      child.spec_id,
                      child.id,
                      child.feature_key,
                      child.category,
                      child.name,
                      child.availability,
                      child.notes,
                      child.source_id,
                      source.source_key,
                      source.name AS source_name,
                      child.source_url,
                      source.license AS source_license,
                      child.observed_at
                    FROM vehicle_features child
                    JOIN sources source ON source.id = child.source_id
                    WHERE child.spec_id = ANY(%s)
                    ORDER BY child.spec_id, child.created_at, child.id
                    """,
                    (spec_ids,),
                ).fetchall()
            )
        )
        media_by_spec = _group_by_spec_id(
            list(
                self.conn.execute(
                    """
                    SELECT
                      child.spec_id,
                      child.id,
                      child.asset_key,
                      child.asset_type,
                      child.title,
                      child.url,
                      child.mime_type,
                      child.locale,
                      child.source_id,
                      source.source_key,
                      source.name AS source_name,
                      child.source_url,
                      source.license AS source_license,
                      child.observed_at
                    FROM vehicle_media_assets child
                    JOIN sources source ON source.id = child.source_id
                    WHERE child.spec_id = ANY(%s)
                    ORDER BY child.spec_id, child.created_at, child.id
                    """,
                    (spec_ids,),
                ).fetchall()
            )
        )

        vehicle_provenance = self.conn.execute(
            """
            SELECT
              provenance.source_id,
              source.source_key,
              source.name AS source_name,
              provenance.source_url,
              source.license AS source_license,
              provenance.observed_at,
              provenance.record_observed_at,
              provenance.content_hash,
              provenance.is_current,
              COALESCE(
                provenance.metadata->'supported_metrics',
                '[]'::jsonb
              ) AS supported_metrics
            FROM vehicle_provenance provenance
            JOIN sources source ON source.id = provenance.source_id
            WHERE provenance.vehicle_id = %s
            ORDER BY provenance.observed_at DESC, source.source_key
            """,
            (vehicle_id,),
        ).fetchall()

        spec_provenance_rows = self.conn.execute(
            """
            SELECT
              provenance.spec_id,
              provenance.source_id,
              source.source_key,
              source.name AS source_name,
              provenance.source_url,
              source.license AS source_license,
              provenance.observed_at,
              provenance.record_observed_at,
              provenance.content_hash,
              provenance.is_current,
              COALESCE(
                provenance.metadata->'supported_metrics',
                '[]'::jsonb
              ) AS supported_metrics
            FROM vehicle_spec_provenance provenance
            JOIN vehicle_specs spec ON spec.id = provenance.spec_id
            JOIN sources source ON source.id = provenance.source_id
            WHERE spec.vehicle_id = %s
            ORDER BY provenance.observed_at DESC, source.source_key
            """,
            (vehicle_id,),
        ).fetchall()
        provenance_by_spec: dict[UUID, list[dict[str, Any]]] = {}
        for row in spec_provenance_rows:
            provenance_by_spec.setdefault(row["spec_id"], []).append(
                {
                    key: value
                    for key, value in row.items()
                    if key != "spec_id"
                }
            )

        specs_with_provenance = []
        for spec in specs:
            maintenance = maintenance_by_spec.get(spec["id"], [])
            ratings = safety_ratings_by_spec.get(spec["id"], [])
            features = features_by_spec.get(spec["id"], [])
            media = media_by_spec.get(spec["id"], [])
            adas = [row for row in features if row["category"] == "adas"]
            safety_equipment = [
                row for row in features if row["category"] == "safety"
            ]
            technology_comfort = [
                row
                for row in features
                if row["category"] in {"technology", "comfort"}
            ]
            power_to_weight = None
            if spec["power_kw"] is not None and spec["curb_weight_kg"]:
                power_to_weight = round(
                    float(spec["power_kw"]) * 1000 / spec["curb_weight_kg"],
                    2,
                )

            profile_spec = {
                **spec,
                "provenance": provenance_by_spec.get(spec["id"], []),
                "identity": {
                    "generation_name": spec["generation_name"],
                    "restyling_label": spec["restyling_label"],
                    "category": spec["category"],
                    "doors": spec["doors"],
                },
                "dimensions": {
                    "length_mm": spec["length_mm"],
                    "width_mm": spec["width_mm"],
                    "height_mm": spec["height_mm"],
                    "wheelbase_mm": spec["wheelbase_mm"],
                    "curb_weight_kg": spec["curb_weight_kg"],
                    "gross_weight_kg": spec["gross_weight_kg"],
                    "payload_kg": spec["payload_kg"],
                    "seats": spec["seats"],
                    "cargo_volume_liters": spec["cargo_volume_liters"],
                },
                "powertrain": {
                    "engine_description": spec["engine"],
                    "engine_code": spec["engine_code"],
                    "displacement_cc": spec["displacement_cc"],
                    "cylinders": spec["cylinders"],
                    "horsepower": spec["horsepower"],
                    "power_kw": spec["power_kw"],
                    "torque_nm": spec["torque_nm"],
                    "fuel_type": spec["fuel_type"],
                    "battery_total_kwh": spec["battery_kwh"],
                    "battery_usable_kwh": spec["battery_usable_kwh"],
                    "wltp_range_km": spec["wltp_range_km"],
                },
                "transmission_details": {
                    "transmission": spec["transmission"],
                    "transmission_type": spec["transmission_type"],
                    "gear_count": spec["gear_count"],
                    "drivetrain": spec["drivetrain"],
                    "differential_type": spec["differential_type"],
                },
                "performance": {
                    "acceleration_0_100_s": spec["acceleration_0_100_s"],
                    "top_speed_kmh": spec["top_speed_kmh"],
                    "braking_100_0_m": spec["braking_100_0_m"],
                    "power_to_weight_kw_per_t": power_to_weight,
                },
                "official_efficiency": {
                    "homologation_cycle": spec["homologation_cycle"],
                    "consumption_l_100km": spec["consumption_l_100km"],
                    "energy_consumption_kwh_100km": spec[
                        "energy_consumption_kwh_100km"
                    ],
                    "co2_g_km": spec["co2_g_km"],
                    "euro_emission_standard": spec["euro_emission_standard"],
                },
                "maintenance_schedule": [
                    {
                        "id": row["id"],
                        "operation_code": row["operation_code"],
                        "title": row["title"],
                        "interval_km": row["interval_km"],
                        "interval_months": row["interval_months"],
                        "notes": row["notes"],
                        "provenance": _profile_provenance(row),
                    }
                    for row in maintenance
                ],
                "safety": {
                    "ratings": [
                        {
                            "id": row["id"],
                            "assessment_system": row["assessment_system"],
                            "assessment_year": row["assessment_year"],
                            "overall_stars": row["overall_stars"],
                            "adult_occupant_percent": row["adult_occupant_percent"],
                            "child_occupant_percent": row["child_occupant_percent"],
                            "vulnerable_road_users_percent": row[
                                "vulnerable_road_users_percent"
                            ],
                            "safety_assist_percent": row["safety_assist_percent"],
                            "provenance": _profile_provenance(row),
                        }
                        for row in ratings
                    ],
                    "adas": [
                        _feature_response(row) for row in adas
                    ],
                    "equipment": [
                        _feature_response(row) for row in safety_equipment
                    ],
                },
                "technology_comfort": [
                    _feature_response(row) for row in technology_comfort
                ],
                "media": [
                    {
                        "id": row["id"],
                        "asset_key": row["asset_key"],
                        "asset_type": row["asset_type"],
                        "title": row["title"],
                        "url": row["url"],
                        "mime_type": row["mime_type"],
                        "locale": row["locale"],
                        "provenance": _profile_provenance(row),
                    }
                    for row in media
                ],
            }
            for field in (
                "generation_name",
                "restyling_label",
                "category",
                "doors",
                "length_mm",
                "width_mm",
                "height_mm",
                "wheelbase_mm",
                "curb_weight_kg",
                "gross_weight_kg",
                "payload_kg",
                "engine_code",
                "displacement_cc",
                "cylinders",
                "power_kw",
                "torque_nm",
                "battery_usable_kwh",
                "transmission_type",
                "gear_count",
                "differential_type",
                "acceleration_0_100_s",
                "top_speed_kmh",
                "braking_100_0_m",
                "homologation_cycle",
            ):
                profile_spec.pop(field)
            specs_with_provenance.append(profile_spec)

        return {
            **vehicle,
            "specs": specs_with_provenance,
            "provenance": list(vehicle_provenance),
        }

    def list_resolve_candidates(self, market: str) -> list[dict[str, Any]]:
        return list(
            self.conn.execute(
                """
                SELECT
                  v.id,
                  v.canonical_key,
                  v.model_family_key,
                  v.make,
                  v.model,
                  v.model_year,
                  COALESCE(s.body_style, v.body_style) AS body_style,
                  COALESCE(s.fuel_type, v.fuel_type) AS fuel_type,
                  v.market,
                  COALESCE(s.list_price_eur, v.base_price_eur) AS base_price_eur,
                  s.id AS spec_id,
                  s.variant_key,
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
                  s.wltp_range_km,
                  s.co2_g_km,
                  s.euro_emission_standard,
                  s.seats,
                  s.cargo_volume_liters
                FROM vehicles v
                LEFT JOIN vehicle_specs s ON s.vehicle_id = v.id
                WHERE v.market = %s
                ORDER BY v.make, v.model, v.model_year, s.trim
                """,
                [market],
            ).fetchall()
        )
