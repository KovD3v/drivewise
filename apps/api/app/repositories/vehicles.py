from typing import Any
from uuid import UUID

from app.repositories.filters import VehicleFilters


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
              cargo_volume_liters
            FROM vehicle_specs
            WHERE vehicle_id = %s
            ORDER BY is_default DESC, trim, variant_key
            """,
            (vehicle_id,),
        ).fetchall()

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

        specs_with_provenance = [
            {
                **spec,
                "provenance": provenance_by_spec.get(spec["id"], []),
            }
            for spec in specs
        ]

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
