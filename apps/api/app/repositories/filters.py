from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class VehicleFilters:
    make: str | None = None
    model: str | None = None
    fuel_type: str | None = None
    body_style: str | None = None
    market: str | None = None
    max_price_eur: float | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class ListingFilters:
    vehicle_id: UUID | None = None
    make: str | None = None
    model: str | None = None
    max_price_eur: float | None = None
    max_mileage: int | None = None
    location_region: str | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class DocumentFilters:
    source_id: UUID | None = None
    vehicle_id: UUID | None = None
    listing_id: UUID | None = None
    document_type: str | None = None
    q: str | None = None
    limit: int = 20
    offset: int = 0
