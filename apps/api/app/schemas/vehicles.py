from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class VehicleProvenance(BaseModel):
    source_id: UUID
    source_key: str
    source_name: str
    source_url: str
    source_license: str | None = None
    observed_at: datetime
    record_observed_at: datetime
    content_hash: str
    is_current: bool
    supported_metrics: list[str] = Field(default_factory=list)


class VehicleSummary(BaseModel):
    id: UUID
    canonical_key: str | None = None
    model_family_key: str | None = None
    make: str
    model: str
    model_year: int
    body_style: str
    fuel_type: str
    market: str
    base_price_eur: float | None = None


class VehicleSpec(BaseModel):
    id: UUID
    variant_key: str | None = None
    is_default: bool = False
    trim: str
    body_style: str | None = None
    fuel_type: str | None = None
    list_price_eur: float | None = None
    drivetrain: str | None = None
    transmission: str | None = None
    engine: str | None = None
    horsepower: int | None = None
    battery_kwh: float | None = None
    energy_consumption_kwh_100km: float | None = None
    consumption_l_100km: float | None = None
    wltp_range_km: int | None = None
    co2_g_km: int | None = None
    euro_emission_standard: str | None = None
    seats: int | None = None
    cargo_volume_liters: float | None = None
    provenance: list[VehicleProvenance] = Field(default_factory=list)


class VehicleDetail(VehicleSummary):
    specs: list[VehicleSpec]
    provenance: list[VehicleProvenance] = Field(default_factory=list)


class VehicleResolveRequest(BaseModel):
    query: str = Field(min_length=2, max_length=160)
    market: str = "IT"
    model_year: int | None = Field(default=None, ge=1980, le=2100)
    fuel_type: str | None = None
    body_style: str | None = None
    limit: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        query = value.strip()
        if len(query) < 2:
            raise ValueError("query must contain at least 2 characters")
        return query

    @field_validator("market")
    @classmethod
    def normalize_market(cls, value: str) -> str:
        return value.strip().upper() or "IT"


class VehicleResolveMatch(BaseModel):
    confidence: float
    match_level: Literal["vehicle", "spec"]
    vehicle: VehicleSummary
    spec: VehicleSpec | None = None
    matched_fields: list[str]
    warnings: list[str]


class VehicleResolveResponse(BaseModel):
    query: str
    normalized_query: str
    status: Literal["matched", "ambiguous", "no_match"]
    matches: list[VehicleResolveMatch]
