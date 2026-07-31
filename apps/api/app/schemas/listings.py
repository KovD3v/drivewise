from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.vehicles import VehicleSpec, VehicleSummary


class ListingWithVehicle(BaseModel):
    id: UUID
    vehicle_id: UUID
    spec_id: UUID | None = None
    source_id: UUID
    source_key: str | None = None
    source_name: str | None = None
    source_license: str | None = None
    source_ranking_permission: str | None = None
    listing_ref: str
    title: str
    price_eur: float | None = None
    mileage: int | None = None
    condition: str
    location_region: str | None = None
    listed_at: date | None = None
    source_url: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True
    content_hash: str | None = None
    vehicle: VehicleSummary
    spec: VehicleSpec | None = None
