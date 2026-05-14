from typing import Any
from uuid import UUID

from app.repositories.filters import VehicleFilters


class VehiclesRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    def list_vehicles(self, filters: VehicleFilters) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[object] = []

        if filters.make:
            where_clauses.append("make ILIKE %s")
            params.append(f"%{filters.make}%")
        if filters.model:
            where_clauses.append("model ILIKE %s")
            params.append(f"%{filters.model}%")
        if filters.fuel_type:
            where_clauses.append("fuel_type = %s")
            params.append(filters.fuel_type)
        if filters.body_style:
            where_clauses.append("body_style = %s")
            params.append(filters.body_style)
        if filters.market:
            where_clauses.append("market = %s")
            params.append(filters.market)
        if filters.max_price_eur is not None:
            where_clauses.append("base_price_eur <= %s")
            params.append(filters.max_price_eur)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT
              id,
              make,
              model,
              model_year,
              body_style,
              fuel_type,
              market,
              base_price_eur
            FROM vehicles
            {where_sql}
            ORDER BY make, model, model_year
            LIMIT %s OFFSET %s
        """

        params.extend([filters.limit, filters.offset])
        return list(self.conn.execute(query, params).fetchall())

    def get_vehicle(self, vehicle_id: UUID) -> dict[str, Any] | None:
        vehicle = self.conn.execute(
            """
            SELECT
              id,
              make,
              model,
              model_year,
              body_style,
              fuel_type,
              market,
              base_price_eur
            FROM vehicles
            WHERE id = %s
            """,
            (vehicle_id,),
        ).fetchone()

        if vehicle is None:
            return None

        specs = self.conn.execute(
            """
            SELECT
              id,
              trim,
              drivetrain,
              transmission,
              engine,
              horsepower,
              battery_kwh,
              consumption_l_100km,
              wltp_range_km,
              co2_g_km,
              euro_emission_standard,
              seats,
              cargo_volume_liters
            FROM vehicle_specs
            WHERE vehicle_id = %s
            ORDER BY trim
            """,
            (vehicle_id,),
        ).fetchall()

        return {**vehicle, "specs": list(specs)}
