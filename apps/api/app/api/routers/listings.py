from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_listings_repository
from app.repositories.filters import ListingFilters
from app.repositories.listings import ListingsRepository
from app.schemas.listings import ListingWithVehicle


router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=list[ListingWithVehicle])
def list_listings(
    repository: Annotated[ListingsRepository, Depends(get_listings_repository)],
    vehicle_id: UUID | None = Query(default=None),
    spec_id: UUID | None = Query(default=None),
    make: str | None = Query(default=None),
    model: str | None = Query(default=None),
    condition: Literal["new", "used", "certified"] | None = Query(default=None),
    active_only: bool = Query(default=True),
    max_price_eur: float | None = Query(default=None, ge=0),
    max_mileage: int | None = Query(default=None, ge=0),
    location_region: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    filters = ListingFilters(
        vehicle_id=vehicle_id,
        spec_id=spec_id,
        make=make,
        model=model,
        condition=condition,
        active_only=active_only,
        max_price_eur=max_price_eur,
        max_mileage=max_mileage,
        location_region=location_region,
        limit=limit,
        offset=offset,
    )
    return repository.list_listings(filters)


@router.get("/{listing_id}", response_model=ListingWithVehicle)
def get_listing(
    listing_id: UUID,
    repository: Annotated[ListingsRepository, Depends(get_listings_repository)],
) -> dict:
    listing = repository.get_listing(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
