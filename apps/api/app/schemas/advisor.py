from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from app.schemas.base import ApiModel
from app.schemas.vehicles import ListPrice, VehicleSpec, VehicleSummary

PrimaryUse = Literal["city", "highway", "family", "work", "new_driver"]
ConstraintMode = Literal["hard", "soft"]
AdvisorPriority = Literal[
    "price",
    "budget",
    "efficiency_range",
    "space",
    "running_cost",
    "family",
    "reliability",
    "safety",
    "comfort",
    "performance",
    "technology",
    "powertrain_fit",
]
AdvisorCondition = Literal["any", "new", "used"]
AdvisorOfferCondition = Literal["new", "used", "certified"]
AdvisorFuelType = Literal[
    "diesel",
    "electric",
    "full_hybrid_petrol",
    "hybrid_petrol",
    "mild_hybrid_petrol",
    "petrol",
    "petrol_lpg",
    "plug_in_hybrid_petrol",
]
AdvisorBodyStyle = Literal[
    "city_car",
    "crossover",
    "hatchback",
    "mpv",
    "sedan",
    "small_hatchback",
    "suv",
    "van",
    "wagon",
]
AdvisorScoreComponent = Literal[
    "price_fit",
    "use_case_fit",
    "running_cost",
    "space",
    "efficiency_range",
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


class AdvisorConstraintModes(ApiModel):
    model_config = ConfigDict(populate_by_name=True)

    budget: ConstraintMode = "soft"
    body_style: ConstraintMode = Field(default="soft", alias="bodyStyle")
    fuel_type: ConstraintMode = Field(default="soft", alias="fuelType")
    transmission: ConstraintMode = "soft"
    garage: ConstraintMode = "soft"


class AdvisorGarageDimensions(ApiModel):
    useful_length_mm: int = Field(gt=0)
    useful_width_mm: int = Field(gt=0)
    useful_height_mm: int = Field(gt=0)
    door_width_mm: int = Field(gt=0)
    door_height_mm: int = Field(gt=0)


class AdvisorRecommendationRequest(ApiModel):
    _annual_km_was_defaulted: bool = PrivateAttr(default=False)

    budget_min_eur: float | None = Field(default=None, ge=0)
    budget_max_eur: float = Field(gt=0)
    primary_use: PrimaryUse
    usage: list[PrimaryUse] | None = None
    children_count: int | None = Field(default=None, ge=0)
    passengers_usual: int | None = Field(default=None, ge=1)
    garage: AdvisorGarageDimensions | None = None
    automatic_required: bool | None = None
    constraint_modes: AdvisorConstraintModes = Field(
        default_factory=AdvisorConstraintModes
    )
    condition: AdvisorCondition = "any"
    annual_km: int | None = Field(default=None, gt=0)
    # Reliable charging access: True, no reliable access: False, unknown: None.
    charging_context: bool | None = None
    preferred_fuel_type: AdvisorFuelType | None = None
    preferred_body_style: AdvisorBodyStyle | None = None
    max_mileage: int | None = Field(default=None, ge=0)
    priorities: list[AdvisorPriority] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_budget_range(self) -> "AdvisorRecommendationRequest":
        if (
            self.budget_min_eur is not None
            and self.budget_min_eur > self.budget_max_eur
        ):
            raise ValueError("budget_min_eur must be less than budget_max_eur")
        if self.annual_km is None:
            self._annual_km_was_defaulted = True
            self.annual_km = {
                "city": 10_000,
                "new_driver": 10_000,
                "family": 14_000,
                "highway": 18_000,
                "work": 18_000,
            }[self.primary_use]
        if self.usage is None:
            self.usage = [self.primary_use]
        return self

    @property
    def annual_km_was_defaulted(self) -> bool:
        return self._annual_km_was_defaulted

    @field_validator("priorities")
    @classmethod
    def reject_duplicate_priorities(
        cls,
        value: list[AdvisorPriority],
    ) -> list[AdvisorPriority]:
        if len(value) != len(set(value)):
            raise ValueError("priorities must not contain duplicates")
        return value

    @field_validator("usage")
    @classmethod
    def reject_duplicate_usage(
        cls,
        value: list[PrimaryUse] | None,
    ) -> list[PrimaryUse] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("usage must not contain duplicates")
        return value


class ModelAnalysisRequest(ApiModel):
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


class ModelAnalysisCostSummary(ApiModel):
    market_reference_price_eur: float | None = None
    # The list price and its source when market_reference_price_eur is the
    # variant's list price; null for any other reference.
    market_reference_list_price: ListPrice | None = None
    estimated_annual_maintenance_eur: float | None = None
    estimated_monthly_energy_eur: float | None = None
    estimated_depreciation_3y_eur: float | None = None
    notes: list[str] = Field(default_factory=list)


class ModelAnalysisResponse(ApiModel):
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


class AdvisorOffer(ApiModel):
    id: UUID
    vehicle_id: UUID
    spec_id: UUID
    source_id: UUID
    listing_ref: str
    title: str
    price_eur: float
    mileage: int | None = None
    condition: AdvisorOfferCondition
    location_region: str | None = None
    source_url: str
    listed_at: date | None = None
    last_seen_at: datetime
    valid_until: datetime | None = None
    is_active: bool

    @field_validator("source_url")
    @classmethod
    def require_https_source_url(cls, value: str) -> str:
        if not value.strip().startswith("https://"):
            raise ValueError("source_url must use https")
        return value


# The list-price block is shared with vehicle detail (ADR-013, ADR-015).
AdvisorListPrice = ListPrice


class AdvisorSelectedSpec(VehicleSpec):
    variant_key: str
    body_style: AdvisorBodyStyle
    fuel_type: AdvisorFuelType


class AdvisorVehicleSummary(VehicleSummary):
    canonical_key: str
    model_family_key: str


class AdvisorFactor(ApiModel):
    component: AdvisorScoreComponent
    message: str
    metric: str | None = None
    value: str | int | float | None = None
    threshold: str | int | float | None = None
    contribution: float


class AdvisorMetricProvenance(ApiModel):
    decision_id: UUID | None = None
    observation_id: UUID | None = None
    metric: str
    source_name: str
    source_url: str
    # Licence or attribution text the product shows next to the source name.
    source_license: str | None = None
    observed_at: date | datetime

    @field_validator("source_url")
    @classmethod
    def require_https_source_url(cls, value: str) -> str:
        if not value.strip().startswith("https://"):
            raise ValueError("source_url must use https")
        return value


class AdvisorRecommendationItem(ApiModel):
    vehicle: AdvisorVehicleSummary
    selected_spec: AdvisorSelectedSpec
    # Null when the variant has no eligible offer and is evaluated at list price.
    offer: AdvisorOffer | None
    price_basis: Literal["offer", "list_price"] = "offer"
    list_price: AdvisorListPrice | None = None
    score: float
    decision_status: Literal["complete", "insufficient_data"] = "insufficient_data"
    decision_score: float | None = None
    decision_confidence: float | None = None
    structural_fit: float | None = None
    preference_fit: float | None = None
    pillar_scores: dict[str, float] = Field(default_factory=dict)
    penalties: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missing_factors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    module_versions: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    score_composition: dict[str, Any] = Field(default_factory=dict)
    component_scores: dict[AdvisorScoreComponent, float | None]
    positive_factors: list[AdvisorFactor]
    tradeoffs: list[AdvisorFactor]
    evidence: dict[str, Any]
    provenance: list[AdvisorMetricProvenance]


    @model_validator(mode="after")
    def price_basis_matches_its_source(self) -> "AdvisorRecommendationItem":
        if (self.price_basis == "offer") != (self.offer is not None):
            raise ValueError("an offer is present exactly when the price basis is offer")
        if (self.price_basis == "list_price") != (self.list_price is not None):
            raise ValueError("a list price is present exactly for the list_price basis")
        return self

    @property
    def price_eur(self) -> float:
        return self.offer.price_eur if self.offer else self.list_price.price_eur

    @property
    def condition_group(self) -> Literal["new", "used"]:
        return "used" if self.offer and self.offer.condition != "new" else "new"


class AdvisorRecommendationGroup(ApiModel):
    condition: Literal["new", "used"]
    items: list[AdvisorRecommendationItem]


class AdvisorRecommendationResponse(ApiModel):
    run_id: UUID
    scoring_version: str
    assumptions: list[str]
    excluded_counts_by_reason: dict[str, int]
    groups: list[AdvisorRecommendationGroup]
    insufficient_data_counts_by_reason: dict[str, int] = Field(default_factory=dict)
