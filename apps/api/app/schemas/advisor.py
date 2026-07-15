from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.vehicles import VehicleSpec, VehicleSummary


PrimaryUse = Literal["city", "highway", "family", "work", "new_driver"]
AdvisorPriority = Literal[
    "price",
    "consumption",
    "reliability",
    "space",
    "safety",
    "range",
]
UsageProfile = Literal["city", "mixed", "highway", "family", "work"]
AnalysisScope = Literal["price", "maintenance", "red_flags", "tco"]
FlowStatus = Literal["completed", "needs_input", "low_confidence", "error"]
ModelAnalysisVerdict = Literal[
    "interesting_with_checks",
    "risky_at_price",
    "not_enough_data",
]
PriceAssessment = Literal["in_range", "above_range", "below_range", "unknown"]
NextAction = Literal[
    "modify_parameters",
    "open_checklist",
    "compare_alternatives",
    "generate_report",
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


class ModelAnalysisRequest(BaseModel):
    query: str | None = Field(default=None, min_length=2, max_length=160)
    vehicle_id: UUID | None = None
    spec_id: UUID | None = None
    market: str = "IT"
    model_year: int | None = Field(default=None, ge=1980, le=2100)
    fuel_type: str | None = None
    body_style: str | None = None
    asking_price_eur: float | None = Field(default=None, ge=0)
    current_km: int | None = Field(default=None, ge=0)
    usage_profile: list[UsageProfile] = Field(default_factory=list)
    analysis_scope: list[AnalysisScope] = Field(
        default_factory=lambda: ["price", "maintenance", "red_flags", "tco"],
        min_length=1,
    )

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        query = value.strip()
        if len(query) < 2:
            raise ValueError("query must contain at least 2 characters")
        return query

    @field_validator("market")
    @classmethod
    def normalize_market(cls, value: str) -> str:
        return value.strip().upper() or "IT"

    @model_validator(mode="after")
    def validate_model_reference(self) -> "ModelAnalysisRequest":
        if self.vehicle_id is None and self.query is None:
            raise ValueError("query or vehicle_id is required")
        return self


class ModelAnalysisCostSummary(BaseModel):
    market_reference_price_eur: float | None = None
    estimated_annual_maintenance_eur: float | None = None
    estimated_monthly_energy_eur: float | None = None
    estimated_depreciation_3y_eur: float | None = None
    notes: list[str] = Field(default_factory=list)


class ModelAnalysisResponse(BaseModel):
    status: FlowStatus
    resolved_vehicle: VehicleSummary | None = None
    resolved_spec: VehicleSpec | None = None
    verdict: ModelAnalysisVerdict
    price_assessment: PriceAssessment
    estimated_costs: ModelAnalysisCostSummary
    red_flags: list[str]
    checklist: list[str]
    confidence: float
    assumptions: list[str]
    warnings: list[str]
    missing_data: list[str]
    next_actions: list[NextAction]


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
