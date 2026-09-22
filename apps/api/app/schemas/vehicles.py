from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.ingestion.catalog_v2 import ExternalReference, MeasurementContext, Metric


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
    vehicle_type: str | None = None
    generation_key: str | None = None
    phase_key: str | None = None
    catalog_version: int = 1
    make: str
    model: str
    model_year: int | None
    body_style: str | None
    fuel_type: str | None
    market: str
    base_price_eur: float | None = None


class VehicleSpec(BaseModel):
    catalog_version: int = 1
    powertrain_type: str | None = None
    fuel: str | None = None
    engine_code: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    external_references: list[ExternalReference] = Field(default_factory=list)
    id: UUID
    variant_key: str | None = None
    is_default: bool = False
    trim: str | None
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


class CatalogFact(BaseModel):
    id: UUID
    spec_id: UUID
    variant_key: str
    metric: Metric
    context: MeasurementContext
    status: Literal["verified", "unknown", "not_applicable", "conflicted"]
    eligible: bool
    value_min: float | None
    value_max: float | None
    unit: str | None
    selected_observation_id: UUID | None
    evidence_ids: list[UUID]
    supersedes_id: UUID | None
    reason: str
    actor_kind: str
    actor_id: str
    policy_version: str
    decided_at: datetime
    source_key: str | None
    source_name: str | None
    source_url: str | None
    retrieved_at: datetime | None
    content_sha256: str | None
    evidence_excerpt: str | None
    evidence_locator: str | None
