from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_vehicles_repository, require_internal_routes
from app.ingestion.catalog_v2 import VehicleType
from app.repositories.filters import VehicleFilters
from app.repositories.vehicles import VehiclesRepository
from app.schemas.vehicles import (
    CatalogFact,
    VehicleDetail,
    VehicleResolveRequest,
    VehicleResolveResponse,
    VehicleSummary,
)
from app.services.vehicles.resolver import resolve_vehicle_query


router = APIRouter(prefix="/vehicles", tags=["vehicles"])

MAX_FILTER_LENGTH = 120


@router.get("", response_model=list[VehicleSummary])
def list_vehicles(
    repository: Annotated[VehiclesRepository, Depends(get_vehicles_repository)],
    make: str | None = Query(default=None, max_length=MAX_FILTER_LENGTH),
    model: str | None = Query(default=None, max_length=MAX_FILTER_LENGTH),
    fuel_type: str | None = Query(default=None, max_length=MAX_FILTER_LENGTH),
    body_style: str | None = Query(default=None, max_length=MAX_FILTER_LENGTH),
    market: str | None = Query(default=None, max_length=MAX_FILTER_LENGTH),
    max_price_eur: float | None = Query(default=None, ge=0),
    vehicle_type: VehicleType | None = Query(default=None),
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
        vehicle_type=vehicle_type,
        limit=limit,
        offset=offset,
    )
    return repository.list_vehicles(filters)


@router.post(
    "/resolve",
    response_model=VehicleResolveResponse,
    dependencies=[Depends(require_internal_routes)],
)
def resolve_vehicle(
    request: VehicleResolveRequest,
    repository: Annotated[VehiclesRepository, Depends(get_vehicles_repository)],
) -> VehicleResolveResponse:
    candidates = repository.list_resolve_candidates(request.market)
    return resolve_vehicle_query(request, candidates)


@router.get("/{vehicle_id}", response_model=VehicleDetail)
def get_vehicle(
    vehicle_id: UUID,
    repository: Annotated[VehiclesRepository, Depends(get_vehicles_repository)],
) -> dict:
    vehicle = repository.get_vehicle(vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.get("/{vehicle_id}/facts", response_model=list[CatalogFact])
def get_vehicle_facts(
    vehicle_id: UUID,
    repository: Annotated[VehiclesRepository, Depends(get_vehicles_repository)],
) -> list[dict]:
    exists = getattr(repository, "vehicle_exists", None)
    found = exists(vehicle_id) if callable(exists) else repository.get_vehicle(vehicle_id) is not None
    if not found:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return repository.list_facts(vehicle_id)
