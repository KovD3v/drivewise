from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.advisor import (
    AdvisorBodyStyle,
    AdvisorCondition,
    AdvisorFuelType,
    AdvisorPriority,
    AdvisorRecommendationGroup,
    AdvisorConstraintModes,
    PrimaryUse,
)


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class GuidedDecisionWireModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )


FactValue = TypeVar("FactValue")
FactSource = Literal["user", "inferred", "imported", "system_default"]
ParkingType = Literal["garage", "covered_space", "outdoor_space", "none"]
DecisionStatus = Literal["active", "completed", "abandoned"]


class DecisionFact(GuidedDecisionWireModel, Generic[FactValue]):
    value: FactValue
    confidence: float = Field(ge=0, le=1)
    source: FactSource
    confirmed: bool
    updated_at: datetime


class GarageProfile(GuidedDecisionWireModel):
    useful_length_mm: DecisionFact[int] | None = None
    useful_width_mm: DecisionFact[int] | None = None
    useful_height_mm: DecisionFact[int] | None = None
    door_width_mm: DecisionFact[int] | None = None
    door_height_mm: DecisionFact[int] | None = None


class DecisionProfile(GuidedDecisionWireModel):
    vehicle_type: DecisionFact[Literal["car"]] | None = None
    category: DecisionFact[AdvisorBodyStyle] | None = None
    budget_eur: DecisionFact[float] | None = None
    family: DecisionFact[bool] | None = None
    primary_use: DecisionFact[PrimaryUse] | None = None
    usage: DecisionFact[list[PrimaryUse]] | None = None
    children_count: DecisionFact[int] | None = None
    passengers_usual: DecisionFact[int] | None = None
    annual_km: DecisionFact[int] | None = None
    condition: DecisionFact[AdvisorCondition] | None = None
    preferred_fuel_type: DecisionFact[AdvisorFuelType] | None = None
    max_mileage_km: DecisionFact[int] | None = None
    priorities: DecisionFact[list[AdvisorPriority]] | None = None
    automatic_required: DecisionFact[bool] | None = None
    constraint_modes: AdvisorConstraintModes = Field(
        default_factory=AdvisorConstraintModes
    )
    parking: DecisionFact[ParkingType] | None = None
    garage: GarageProfile = Field(default_factory=GarageProfile)


class MissingInformation(GuidedDecisionWireModel):
    key: str
    priority: float = Field(ge=0, le=1)
    reason: str
    affects: list[str] = Field(default_factory=list)


class QuestionConstraints(GuidedDecisionWireModel):
    minimum: float | None = None
    maximum: float | None = None
    unit: str | None = None
    options: list[str] = Field(default_factory=list)


class NextQuestion(GuidedDecisionWireModel):
    id: str
    type: Literal["number", "boolean", "single_select", "multi_select", "text"]
    label: str
    reason: str
    constraints: QuestionConstraints | None = None


RankingStatus = Literal[
    "blocked",
    "ready",
    "insufficient_inventory",
]


class PreviewRanking(GuidedDecisionWireModel):
    status: RankingStatus
    scoring_version: str | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    groups: list[AdvisorRecommendationGroup] = Field(default_factory=list)


GarageCompatibilityStatus = Literal[
    "comfortable",
    "tight",
    "incompatible",
    "insufficient_data",
]


class GarageMargins(GuidedDecisionWireModel):
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    door_width_mm: int | None = None
    door_height_mm: int | None = None


class GarageCompatibility(GuidedDecisionWireModel):
    vehicle_id: UUID
    spec_id: UUID
    status: GarageCompatibilityStatus
    message: str
    margins: GarageMargins | None = None
    missing_data: list[str] = Field(default_factory=list)
    evaluation_version: str | None = None


class CreateGuidedDecisionRequest(GuidedDecisionWireModel):
    message: str = Field(min_length=1, max_length=2_000)
    locale: str = Field(default="it-IT", min_length=2, max_length=20)
    market: str = Field(default="IT", min_length=2, max_length=3)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        return value.strip()

    @field_validator("locale")
    @classmethod
    def normalize_locale(cls, value: str) -> str:
        return value.strip() or "it-IT"

    @field_validator("market")
    @classmethod
    def normalize_market(cls, value: str) -> str:
        market = value.strip().upper()
        if market != "IT":
            raise ValueError("guided-decision-v1 supports only the IT market")
        return market


class AddGuidedDecisionTurnRequest(GuidedDecisionWireModel):
    message: str = Field(min_length=1, max_length=2_000)
    expected_profile_version: int = Field(ge=1)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        return value.strip()


class GuidedDecisionResponse(GuidedDecisionWireModel):
    contract_version: Literal["guided-decision-v1"] = "guided-decision-v1"
    decision_id: UUID
    profile_version: int
    status: DecisionStatus
    message: str
    decision_profile: DecisionProfile
    updated_fields: list[str]
    profile_completion: float = Field(ge=0, le=1)
    decision_confidence: float = Field(ge=0, le=1)
    missing_information: list[MissingInformation]
    next_question: NextQuestion | None
    preview_ranking: PreviewRanking
    garage_compatibility: list[GarageCompatibility] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GuidedDecisionRecord(BaseModel):
    id: UUID
    locale: str
    market: str
    status: DecisionStatus
    profile_version: int
    decision_profile: DecisionProfile
    last_response: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
