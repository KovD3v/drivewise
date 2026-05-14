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
        if filters.make:
            where_clauses.append("v.make ILIKE %s")
            params.append(f"%{filters.make}%")
        if filters.model:
            where_clauses.append("v.model ILIKE %s")
            params.append(f"%{filters.model}%")
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
              l.source_id,
              l.listing_ref,
              l.title,
              l.price_eur,
              l.mileage,
              l.condition,
              l.location_region,
              l.listed_at,
              v.id AS vehicle_id_nested,
              v.make,
              v.model,
              v.model_year,
              v.body_style,
              v.fuel_type,
              v.market,
              v.base_price_eur
            FROM listings l
            JOIN vehicles v ON v.id = l.vehicle_id
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
              l.source_id,
              l.listing_ref,
              l.title,
              l.price_eur,
              l.mileage,
              l.condition,
              l.location_region,
              l.listed_at,
              v.id AS vehicle_id_nested,
              v.make,
              v.model,
              v.model_year,
              v.body_style,
              v.fuel_type,
              v.market,
              v.base_price_eur
            FROM listings l
            JOIN vehicles v ON v.id = l.vehicle_id
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
            "source_id": row["source_id"],
            "listing_ref": row["listing_ref"],
            "title": row["title"],
            "price_eur": row["price_eur"],
            "mileage": row["mileage"],
            "condition": row["condition"],
            "location_region": row["location_region"],
            "listed_at": row["listed_at"],
            "vehicle": {
                "id": row["vehicle_id_nested"],
                "make": row["make"],
                "model": row["model"],
                "model_year": row["model_year"],
                "body_style": row["body_style"],
                "fuel_type": row["fuel_type"],
                "market": row["market"],
                "base_price_eur": row["base_price_eur"],
            },
        }
