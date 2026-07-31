from typing import Any
from uuid import UUID

from app.repositories.filters import ListingFilters


class ListingsRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    def list_listings(self, filters: ListingFilters) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[object] = []

        if filters.vehicle_id:
            where_clauses.append("l.vehicle_id = %s")
            params.append(filters.vehicle_id)
        if filters.spec_id:
            where_clauses.append("l.spec_id = %s")
            params.append(filters.spec_id)
        if filters.make:
            where_clauses.append("v.make ILIKE %s")
            params.append(f"%{filters.make}%")
        if filters.model:
            where_clauses.append("v.model ILIKE %s")
            params.append(f"%{filters.model}%")
        if filters.condition:
            where_clauses.append("l.condition = %s")
            params.append(filters.condition)
        if filters.active_only:
            where_clauses.append("l.is_active")
        if filters.max_price_eur is not None:
            where_clauses.append("l.price_eur <= %s")
            params.append(filters.max_price_eur)
        if filters.max_mileage is not None:
            where_clauses.append("l.mileage <= %s")
            params.append(filters.max_mileage)
        if filters.location_region:
            where_clauses.append("l.location_region ILIKE %s")
            params.append(f"%{filters.location_region}%")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT
              l.id,
              l.vehicle_id,
              l.spec_id,
              l.source_id,
              source.source_key,
              source.name AS source_name,
              source.license AS source_license,
              source.ranking_permission AS source_ranking_permission,
              l.listing_ref,
              l.title,
              l.price_eur,
              l.mileage,
              l.condition,
              l.location_region,
              l.listed_at,
              l.source_url,
              l.first_seen_at,
              l.last_seen_at,
              l.valid_until,
              l.is_active,
              l.content_hash,
              v.id AS vehicle_id_nested,
              v.canonical_key,
              v.model_family_key,
              v.make,
              v.model,
              v.model_year,
              COALESCE(spec.body_style, v.body_style) AS body_style,
              COALESCE(spec.fuel_type, v.fuel_type) AS fuel_type,
              v.market,
              COALESCE(spec.list_price_eur, v.base_price_eur) AS base_price_eur,
              spec.id AS spec_id_nested,
              spec.variant_key,
              spec.is_default,
              spec.trim,
              spec.body_style AS spec_body_style,
              spec.fuel_type AS spec_fuel_type,
              spec.list_price_eur,
              spec.drivetrain,
              spec.transmission,
              spec.engine,
              spec.horsepower,
              spec.battery_kwh,
              spec.energy_consumption_kwh_100km,
              spec.consumption_l_100km,
              spec.wltp_range_km,
              spec.co2_g_km,
              spec.euro_emission_standard,
              spec.seats,
              spec.cargo_volume_liters
            FROM listings l
            JOIN vehicles v ON v.id = l.vehicle_id
            JOIN sources source ON source.id = l.source_id
            LEFT JOIN vehicle_specs spec
              ON spec.id = l.spec_id AND spec.vehicle_id = l.vehicle_id
            {where_sql}
            ORDER BY l.listed_at DESC NULLS LAST, l.created_at DESC
            LIMIT %s OFFSET %s
        """

        params.extend([filters.limit, filters.offset])
        return [self._row_to_listing(row) for row in self.conn.execute(query, params)]

    def get_listing(self, listing_id: UUID) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT
              l.id,
              l.vehicle_id,
              l.spec_id,
              l.source_id,
              source.source_key,
              source.name AS source_name,
              source.license AS source_license,
              source.ranking_permission AS source_ranking_permission,
              l.listing_ref,
              l.title,
              l.price_eur,
              l.mileage,
              l.condition,
              l.location_region,
              l.listed_at,
              l.source_url,
              l.first_seen_at,
              l.last_seen_at,
              l.valid_until,
              l.is_active,
              l.content_hash,
              v.id AS vehicle_id_nested,
              v.canonical_key,
              v.model_family_key,
              v.make,
              v.model,
              v.model_year,
              COALESCE(spec.body_style, v.body_style) AS body_style,
              COALESCE(spec.fuel_type, v.fuel_type) AS fuel_type,
              v.market,
              COALESCE(spec.list_price_eur, v.base_price_eur) AS base_price_eur,
              spec.id AS spec_id_nested,
              spec.variant_key,
              spec.is_default,
              spec.trim,
              spec.body_style AS spec_body_style,
              spec.fuel_type AS spec_fuel_type,
              spec.list_price_eur,
              spec.drivetrain,
              spec.transmission,
              spec.engine,
              spec.horsepower,
              spec.battery_kwh,
              spec.energy_consumption_kwh_100km,
              spec.consumption_l_100km,
              spec.wltp_range_km,
              spec.co2_g_km,
              spec.euro_emission_standard,
              spec.seats,
              spec.cargo_volume_liters
            FROM listings l
            JOIN vehicles v ON v.id = l.vehicle_id
            JOIN sources source ON source.id = l.source_id
            LEFT JOIN vehicle_specs spec
              ON spec.id = l.spec_id AND spec.vehicle_id = l.vehicle_id
            WHERE l.id = %s
            """,
            (listing_id,),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_listing(row)

    def _row_to_listing(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "vehicle_id": row["vehicle_id"],
            "spec_id": row["spec_id"],
            "source_id": row["source_id"],
            "source_key": row["source_key"],
            "source_name": row["source_name"],
            "source_license": row["source_license"],
            "source_ranking_permission": row["source_ranking_permission"],
            "listing_ref": row["listing_ref"],
            "title": row["title"],
            "price_eur": row["price_eur"],
            "mileage": row["mileage"],
            "condition": row["condition"],
            "location_region": row["location_region"],
            "listed_at": row["listed_at"],
            "source_url": row["source_url"],
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"],
            "valid_until": row["valid_until"],
            "is_active": row["is_active"],
            "content_hash": row["content_hash"],
            "vehicle": {
                "id": row["vehicle_id_nested"],
                "canonical_key": row["canonical_key"],
                "model_family_key": row["model_family_key"],
                "make": row["make"],
                "model": row["model"],
                "model_year": row["model_year"],
                "body_style": row["body_style"],
                "fuel_type": row["fuel_type"],
                "market": row["market"],
                "base_price_eur": row["base_price_eur"],
            },
            "spec": self._row_to_spec(row),
        }

    def _row_to_spec(self, row: dict[str, Any]) -> dict[str, Any] | None:
        if row["spec_id_nested"] is None:
            return None
        return {
            "id": row["spec_id_nested"],
            "variant_key": row["variant_key"],
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
            "wltp_range_km": row["wltp_range_km"],
            "co2_g_km": row["co2_g_km"],
            "euro_emission_standard": row["euro_emission_standard"],
            "seats": row["seats"],
            "cargo_volume_liters": row["cargo_volume_liters"],
        }
