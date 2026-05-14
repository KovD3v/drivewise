from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_vehicles_repository
from app.repositories.filters import VehicleFilters
from app.repositories.vehicles import VehiclesRepository
from app.schemas.vehicles import VehicleDetail, VehicleSummary


router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleSummary])
def list_vehicles(
    repository: Annotated[VehiclesRepository, Depends(get_vehicles_repository)],
    make: str | None = Query(default=None),
    model: str | None = Query(default=None),
    fuel_type: str | None = Query(default=None),
    body_style: str | None = Query(default=None),
    market: str | None = Query(default=None),
    max_price_eur: float | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    filters = VehicleFilters(
        make=make,
        model=model,
        fuel_type=fuel_type,
        body_style=body_style,
        market=market,
        max_price_eur=max_price_eur,
        limit=limit,
        offset=offset,
    )
    return repository.list_vehicles(filters)


@router.get("/{vehicle_id}", response_model=VehicleDetail)
def get_vehicle(
    vehicle_id: UUID,
    repository: Annotated[VehiclesRepository, Depends(get_vehicles_repository)],
) -> dict:
    vehicle = repository.get_vehicle(vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle
