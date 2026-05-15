from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class VehicleSummary(BaseModel):
    id: UUID
    make: str
    model: str
    model_year: int
    body_style: str
    fuel_type: str
    market: str
    base_price_eur: float | None = None


class VehicleSpec(BaseModel):
    id: UUID
    trim: str
    drivetrain: str | None = None
    transmission: str | None = None
    engine: str | None = None
    horsepower: int | None = None
    battery_kwh: float | None = None
    consumption_l_100km: float | None = None
    wltp_range_km: int | None = None
    co2_g_km: int | None = None
    euro_emission_standard: str | None = None
    seats: int | None = None
    cargo_volume_liters: float | None = None


class VehicleDetail(VehicleSummary):
    specs: list[VehicleSpec]


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
    match_level: str
    vehicle: VehicleSummary
    spec: VehicleSpec | None = None
    matched_fields: list[str]
    warnings: list[str]


class VehicleResolveResponse(BaseModel):
    query: str
    normalized_query: str
    status: str
    matches: list[VehicleResolveMatch]
