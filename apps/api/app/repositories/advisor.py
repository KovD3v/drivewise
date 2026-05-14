from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.schemas.advisor import AdvisorRecommendationItem


class AdvisorRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    def list_candidates(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
              v.id AS vehicle_id,
              v.make,
              v.model,
              v.model_year,
              v.body_style,
              v.fuel_type,
              v.market,
              v.base_price_eur,
              s.id AS spec_id,
              s.trim,
              s.drivetrain,
              s.transmission,
              s.engine,
              s.horsepower,
              s.battery_kwh,
              s.consumption_l_100km,
              s.wltp_range_km,
              s.co2_g_km,
              s.euro_emission_standard,
              s.seats,
              s.cargo_volume_liters,
              l.id AS listing_id,
              l.source_id,
              l.listing_ref,
              l.title,
              l.price_eur,
              l.mileage,
              l.condition,
              l.location_region,
              l.listed_at
            FROM vehicles v
            LEFT JOIN vehicle_specs s ON s.vehicle_id = v.id
            LEFT JOIN listings l ON l.vehicle_id = v.id
            ORDER BY v.make, v.model, s.trim, l.price_eur NULLS LAST
            """
        ).fetchall()

        candidates: dict[UUID, dict[str, Any]] = {}
        seen_specs: set[UUID] = set()
        seen_listings: set[UUID] = set()

        for row in rows:
            vehicle_id = row["vehicle_id"]
            candidate = candidates.setdefault(
                vehicle_id,
                {
                    "vehicle": {
                        "id": vehicle_id,
                        "make": row["make"],
                        "model": row["model"],
                        "model_year": row["model_year"],
                        "body_style": row["body_style"],
                        "fuel_type": row["fuel_type"],
                        "market": row["market"],
                        "base_price_eur": row["base_price_eur"],
                    },
                    "specs": [],
                    "listings": [],
                },
            )

            spec_id = row["spec_id"]
            if spec_id is not None and spec_id not in seen_specs:
                seen_specs.add(spec_id)
                candidate["specs"].append(
                    {
                        "id": spec_id,
                        "trim": row["trim"],
                        "drivetrain": row["drivetrain"],
                        "transmission": row["transmission"],
                        "engine": row["engine"],
                        "horsepower": row["horsepower"],
                        "battery_kwh": row["battery_kwh"],
                        "consumption_l_100km": row["consumption_l_100km"],
                        "wltp_range_km": row["wltp_range_km"],
                        "co2_g_km": row["co2_g_km"],
                        "euro_emission_standard": row["euro_emission_standard"],
                        "seats": row["seats"],
                        "cargo_volume_liters": row["cargo_volume_liters"],
                    }
                )

            listing_id = row["listing_id"]
            if listing_id is not None and listing_id not in seen_listings:
                seen_listings.add(listing_id)
                candidate["listings"].append(
                    {
                        "id": listing_id,
                        "vehicle_id": vehicle_id,
                        "source_id": row["source_id"],
                        "listing_ref": row["listing_ref"],
                        "title": row["title"],
                        "price_eur": row["price_eur"],
                        "mileage": row["mileage"],
                        "condition": row["condition"],
                        "location_region": row["location_region"],
                        "listed_at": row["listed_at"].isoformat()
                        if row["listed_at"]
                        else None,
                    }
                )

        return list(candidates.values())

    def create_run(self, request_payload: dict[str, Any]) -> UUID:
        run_id = uuid4()
        self.conn.execute(
            """
            INSERT INTO recommendation_runs (id, request_payload, status)
            VALUES (%s, %s, 'queued')
            """,
            (run_id, Jsonb(request_payload)),
        )
        return run_id

    def save_items(
        self,
        run_id: UUID,
        items: list[AdvisorRecommendationItem],
    ) -> None:
        for rank, item in enumerate(items, start=1):
            self.conn.execute(
                """
                INSERT INTO recommendation_items (
                  id,
                  run_id,
                  vehicle_id,
                  rank,
                  score,
                  rationale
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    run_id,
                    item.vehicle.id,
                    rank,
                    item.score,
                    item.rationale,
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
