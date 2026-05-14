from uuid import UUID

from pydantic import BaseModel


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
