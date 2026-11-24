from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.ingestion.catalog_v2 import (
    ExternalReference,
    MeasurementContext,
    Metric,
    VehicleType,
)
from app.schemas.base import ApiModel


class VehicleProvenance(ApiModel):
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


class VehicleSummary(ApiModel):
    id: UUID
    canonical_key: str | None = None
    model_family_key: str | None = None
    # Null only for legacy (catalog v1) rows, whose contract is car-only.
    vehicle_type: VehicleType | None = None
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


class ProfileProvenance(ApiModel):
    source_id: UUID
    source_key: str
    source_name: str
    source_url: str
    source_license: str | None = None
    observed_at: datetime


class VehicleIdentity(ApiModel):
    generation_name: str | None = None
    restyling_label: str | None = None
    category: str | None = None
    doors: int | None = None


class VehicleDimensions(ApiModel):
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    wheelbase_mm: int | None = None
    curb_weight_kg: int | None = None
    gross_weight_kg: int | None = None
    payload_kg: int | None = None
    seats: int | None = None
    cargo_volume_liters: float | None = None


class VehiclePowertrain(ApiModel):
    engine_description: str | None = None
    engine_code: str | None = None
    displacement_cc: int | None = None
    cylinders: int | None = None
    horsepower: int | None = None
    power_kw: float | None = None
    torque_nm: int | None = None
    fuel_type: str | None = None
    battery_total_kwh: float | None = None
    battery_usable_kwh: float | None = None
    wltp_range_km: int | None = None


class VehicleTransmission(ApiModel):
    transmission: str | None = None
    transmission_type: str | None = None
    gear_count: int | None = None
    drivetrain: str | None = None
    differential_type: str | None = None


class VehiclePerformance(ApiModel):
    acceleration_0_100_s: float | None = None
    top_speed_kmh: int | None = None
    braking_100_0_m: float | None = None
    power_to_weight_kw_per_t: float | None = None


class VehicleOfficialEfficiency(ApiModel):
    homologation_cycle: str | None = None
    consumption_l_100km: float | None = None
    energy_consumption_kwh_100km: float | None = None
    co2_g_km: int | None = None
    euro_emission_standard: str | None = None


class VehicleMaintenanceItem(ApiModel):
    id: UUID
    operation_code: str
    title: str
    interval_km: int | None = None
    interval_months: int | None = None
    notes: str | None = None
    provenance: ProfileProvenance


class VehicleSafetyRating(ApiModel):
    id: UUID
    assessment_system: str
    assessment_year: int
    overall_stars: int | None = None
    adult_occupant_percent: int | None = None
    child_occupant_percent: int | None = None
    vulnerable_road_users_percent: int | None = None
    safety_assist_percent: int | None = None
    provenance: ProfileProvenance


class VehicleFeature(ApiModel):
    id: UUID
    feature_key: str
    category: Literal["adas", "safety", "technology", "comfort"]
    name: str
    availability: Literal["standard", "optional"]
    notes: str | None = None
    provenance: ProfileProvenance


class VehicleSafety(ApiModel):
    ratings: list[VehicleSafetyRating] = Field(default_factory=list)
    adas: list[VehicleFeature] = Field(default_factory=list)
    equipment: list[VehicleFeature] = Field(default_factory=list)


class VehicleMediaAsset(ApiModel):
    id: UUID
    asset_key: str
    asset_type: Literal["photo", "brochure", "manual"]
    title: str
    url: str
    mime_type: str | None = None
    locale: str | None = None
    provenance: ProfileProvenance


class VehicleTwoWheelSpecs(ApiModel):
    """Reviewed point values from catalog v2 facts; null when unknown or ambiguous."""

    seat_height_mm: float | None = None
    wet_weight_kg: float | None = None
    fuel_tank_capacity_liters: float | None = None
    underseat_storage_liters: float | None = None


class VehicleSpec(ApiModel):
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


class VehicleSpecDetail(VehicleSpec):
    identity: VehicleIdentity = Field(default_factory=VehicleIdentity)
    dimensions: VehicleDimensions = Field(default_factory=VehicleDimensions)
    powertrain: VehiclePowertrain = Field(default_factory=VehiclePowertrain)
    transmission_details: VehicleTransmission = Field(
        default_factory=VehicleTransmission
    )
    performance: VehiclePerformance = Field(default_factory=VehiclePerformance)
    official_efficiency: VehicleOfficialEfficiency = Field(
        default_factory=VehicleOfficialEfficiency
    )
    maintenance_schedule: list[VehicleMaintenanceItem] = Field(default_factory=list)
    safety: VehicleSafety = Field(default_factory=VehicleSafety)
    technology_comfort: list[VehicleFeature] = Field(default_factory=list)
    media: list[VehicleMediaAsset] = Field(default_factory=list)
    two_wheel: VehicleTwoWheelSpecs = Field(default_factory=VehicleTwoWheelSpecs)


class VehicleDetail(VehicleSummary):
    specs: list[VehicleSpecDetail]
    provenance: list[VehicleProvenance] = Field(default_factory=list)


class VehicleResolveRequest(ApiModel):
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


class VehicleResolveMatch(ApiModel):
    confidence: float
    match_level: Literal["vehicle", "spec"]
    vehicle: VehicleSummary
    spec: VehicleSpec | None = None
    matched_fields: list[str]
    warnings: list[str]


class VehicleResolveResponse(ApiModel):
    query: str
    normalized_query: str
    status: Literal["matched", "ambiguous", "no_match"]
    matches: list[VehicleResolveMatch]


class CatalogFact(ApiModel):
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
