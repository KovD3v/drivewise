from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.vehicles import VehicleSummary


class ListingWithVehicle(BaseModel):
    id: UUID
    vehicle_id: UUID
    source_id: UUID
    listing_ref: str
    title: str
    price_eur: float | None = None
    mileage: int | None = None
    condition: str
    location_region: str | None = None
    listed_at: date | None = None
    vehicle: VehicleSummary
