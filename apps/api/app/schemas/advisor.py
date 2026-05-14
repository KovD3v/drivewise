from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.vehicles import VehicleSummary


PrimaryUse = Literal["city", "highway", "family", "work", "new_driver"]
AdvisorPriority = Literal[
    "price",
    "consumption",
    "reliability",
    "space",
    "safety",
    "range",
]


class AdvisorRecommendationRequest(BaseModel):
    budget_min_eur: float | None = Field(default=None, ge=0)
    budget_max_eur: float = Field(gt=0)
    primary_use: PrimaryUse
    preferred_fuel_type: str | None = None
    preferred_body_style: str | None = None
    max_mileage: int | None = Field(default=None, ge=0)
    priorities: list[AdvisorPriority] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_budget_range(self) -> "AdvisorRecommendationRequest":
        if (
            self.budget_min_eur is not None
            and self.budget_min_eur > self.budget_max_eur
        ):
            raise ValueError("budget_min_eur must be less than budget_max_eur")
        return self


class AdvisorListingSummary(BaseModel):
    id: UUID
    vehicle_id: UUID
    source_id: UUID
    listing_ref: str
    title: str
    price_eur: float | None = None
    mileage: int | None = None
    condition: str
    location_region: str | None = None
    listed_at: str | None = None


class AdvisorDocumentEvidence(BaseModel):
    document_id: UUID
    title: str
    document_type: str
    score: float
    snippet: str


class AdvisorRecommendationItem(BaseModel):
    vehicle: VehicleSummary
    best_listing: AdvisorListingSummary | None
    score: float
    rationale: str
    evidence: dict[str, Any]
    document_evidence: list[AdvisorDocumentEvidence] = Field(default_factory=list)


class AdvisorRecommendationResponse(BaseModel):
    run_id: UUID
    items: list[AdvisorRecommendationItem]
