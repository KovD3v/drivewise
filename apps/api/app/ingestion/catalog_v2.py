"""Catalog v2 evidence contract. Validation only; publication is a separate step."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    ValidationError,
    model_validator,
)

from app.ingestion.catalog import CatalogValidationError, SourceRecord


Key = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]*$", max_length=240)]
Text = Annotated[str, Field(min_length=1, max_length=500)]
Number = Annotated[Decimal, Field(allow_inf_nan=False)]
Metric = Literal[
    "engine_power_kw",
    "system_power_kw",
    "continuous_power_kw",
    "engine_displacement_cc",
    "cylinders",
    "battery_gross_kwh",
    "battery_usable_kwh",
    "liquid_consumption_l_100km",
    "electric_consumption_kwh_100km",
    "electric_range_km",
    "co2_g_km",
    "length_mm",
    "body_width_mm",
    "width_with_mirrors_mm",
    "height_mm",
    "seats",
    "cargo_volume_liters",
    "mass_kg",
    "ac_charge_power_kw",
    "dc_peak_charge_power_kw",
]
# The unit is part of the metric definition, never guessed from a source label.
METRIC_UNITS = {
    "engine_power_kw": "kW",
    "system_power_kw": "kW",
    "continuous_power_kw": "kW",
    "engine_displacement_cc": "cm3",
    "cylinders": "count",
    "battery_gross_kwh": "kWh",
    "battery_usable_kwh": "kWh",
    "liquid_consumption_l_100km": "l/100km",
    "electric_consumption_kwh_100km": "kWh/100km",
    "electric_range_km": "km",
    "co2_g_km": "g/km",
    "length_mm": "mm",
    "body_width_mm": "mm",
    "width_with_mirrors_mm": "mm",
    "height_mm": "mm",
    "seats": "count",
    "cargo_volume_liters": "l",
    "mass_kg": "kg",
    "ac_charge_power_kw": "kW",
    "dc_peak_charge_power_kw": "kW",
}
MEASURED_METRICS = {
    "liquid_consumption_l_100km",
    "electric_consumption_kwh_100km",
    "electric_range_km",
    "co2_g_km",
}


def _country(value: str) -> str:
    if value in {"EU", "ZZ", "XX"}:
        raise ValueError("a national market is required, not a regional/unknown code")
    return value


Market = Annotated[str, Field(pattern=r"^[A-Z]{2}$"), AfterValidator(_country)]


class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class Applicability(ContractModel):
    valid_from: date | None = None
    valid_to: date | None = None

    @model_validator(mode="after")
    def ordered_dates(self) -> Self:
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_to precedes valid_from")
        return self

    def overlaps(self, other: "Applicability") -> bool:
        return not (
            self.valid_from and other.valid_to and other.valid_to < self.valid_from
        ) and not (
            self.valid_to and other.valid_from and other.valid_from > self.valid_to
        )


class ExternalReference(ContractModel):
    namespace: Key
    value: Text
    # References are evidence identifiers, not globally unique commercial keys.


class VehicleIdentity(ContractModel):
    canonical_key: Key
    model_family_key: Key
    make: Text
    model: Text
    vehicle_type: Literal["car", "motorcycle", "scooter"]
    generation_key: Key | None
    phase_key: Key | None
    body_style: Key | None
    model_year: Annotated[int, Field(strict=True, ge=1980, le=2100)] | None
    market: Market
    evidence_snapshot_ids: list[UUID] = Field(min_length=1)


class VariantIdentity(Applicability):
    variant_key: Key
    vehicle_key: Key
    trim: Text | None
    powertrain_type: Literal["ICE", "MHEV", "HEV", "PHEV", "BEV"] | None
    fuel: Literal["petrol", "diesel", "electricity", "petrol_lpg", "hydrogen"] | None
    transmission: Key | None
    drivetrain: Literal["FWD", "RWD", "AWD"] | None
    engine_code: Text | None = None
    external_references: list[ExternalReference] = Field(default_factory=list)
    evidence_snapshot_ids: list[UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_powertrain(self) -> Self:
        if self.powertrain_type == "BEV" and self.fuel not in {None, "electricity"}:
            raise ValueError("BEV cannot have a liquid fuel")
        if self.powertrain_type in {"ICE", "MHEV", "HEV", "PHEV"}:
            if self.fuel == "electricity":
                raise ValueError("combustion/hybrid powertrains require their fuel")
        return self


class SourceSnapshot(ContractModel):
    id: UUID
    source_key: Key
    url: HttpUrl
    retrieved_at: AwareDatetime
    published_at: AwareDatetime | None = None
    content_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    artifact_path: Text
    media_type: Text
    evidence_kind: Literal["sourced", "synthetic", "legacy"]

    @model_validator(mode="after")
    def safe_artifact_path(self) -> Self:
        path = Path(self.artifact_path)
        if path.is_absolute() or ".." in path.parts or "\\" in self.artifact_path:
            raise ValueError("artifact_path must be a relative path without traversal")
        if self.published_at and self.published_at > self.retrieved_at:
            raise ValueError("published_at cannot follow retrieved_at")
        return self


class MeasurementContext(Applicability):
    market: Market
    procedure: Literal["WLTP", "NEDC", "declared", "measured", "unknown"] | None = None
    cycle: (
        Literal["combined", "urban", "highway", "weighted_combined", "unknown"] | None
    ) = None
    configuration_key: Key | None = None
    method: Text | None = None
    seating_configuration: Text | None = None
    battery_condition: (
        Literal["charge_depleting", "charge_sustaining", "weighted", "unknown"] | None
    ) = None

    @model_validator(mode="after")
    def fits_storage_key(self) -> Self:
        # Keep the complete context in composite FKs, within PostgreSQL's B-tree limit.
        encoded = json.dumps(self.model_dump(mode="json"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > 1800:
            raise ValueError("measurement context exceeds 1800 UTF-8 bytes")
        return self


class SpecObservation(ContractModel):
    model_config = ConfigDict(json_schema_extra={"x-metric-units": METRIC_UNITS})

    id: UUID
    snapshot_id: UUID
    variant_key: Key | None
    candidate_variant_keys: list[Key] = Field(default_factory=list)
    metric: Metric
    raw_value: Text
    raw_unit: Text | None
    value_min: Number
    value_max: Number
    unit: Text
    context: MeasurementContext
    evidence_excerpt: Annotated[str, Field(min_length=1, max_length=4000)]
    evidence_locator: Text
    extractor_version: Key

    @model_validator(mode="after")
    def valid_measurement(self) -> Self:
        if self.variant_key and self.candidate_variant_keys:
            raise ValueError(
                "resolved observations cannot also have candidate variants"
            )
        if len(self.candidate_variant_keys) != len(set(self.candidate_variant_keys)):
            raise ValueError("duplicate candidate variants")
        if self.unit != METRIC_UNITS[self.metric]:
            raise ValueError(f"{self.metric} requires unit {METRIC_UNITS[self.metric]}")
        zero_allowed = self.metric in {"co2_g_km", "cargo_volume_liters"}
        if self.value_min < 0 or (self.value_min == 0 and not zero_allowed):
            raise ValueError("measurement must be positive (zero is not unknown)")
        if self.value_max < self.value_min:
            raise ValueError("value_max precedes value_min")
        if self.metric in {"seats", "cylinders"}:
            if (
                self.value_min != self.value_min.to_integral_value()
                or self.value_max != self.value_max.to_integral_value()
            ):
                raise ValueError("counts must be integers")
        if self.metric in MEASURED_METRICS:
            if self.context.procedure is None or self.context.cycle is None:
                raise ValueError(
                    "consumption/range/emissions require procedure and cycle"
                )
        if self.metric == "cargo_volume_liters":
            if not self.context.method or not self.context.seating_configuration:
                raise ValueError(
                    "cargo volume requires method and seating configuration"
                )
        if self.metric == "mass_kg" and not self.context.method:
            raise ValueError("mass requires its measurement definition")
        return self


class FactDecision(ContractModel):
    id: UUID
    variant_key: Key
    metric: Metric
    context: MeasurementContext
    status: Literal["verified", "unknown", "not_applicable", "conflicted"]
    selected_observation_id: UUID | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    supersedes_id: UUID | None = None
    reason: Text
    actor_kind: Literal["human", "rule", "agent"]
    actor_id: Key
    policy_version: Key
    decided_at: AwareDatetime

    @model_validator(mode="after")
    def valid_selection(self) -> Self:
        if (self.status == "verified") != (self.selected_observation_id is not None):
            raise ValueError("only verified decisions must select an observation")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("duplicate evidence IDs")
        if (
            self.selected_observation_id
            and self.selected_observation_id not in self.evidence_ids
        ):
            raise ValueError("selected observation must be included in evidence_ids")
        if self.status == "conflicted" and len(self.evidence_ids) < 2:
            raise ValueError("conflicted decisions require competing observations")
        if self.supersedes_id == self.id:
            raise ValueError("a decision cannot supersede itself")
        return self


def _index(records: list, field: str) -> dict:
    indexed = {getattr(record, field): record for record in records}
    if len(indexed) != len(records):
        raise ValueError(f"duplicate {field}")
    return indexed


class CatalogV2(ContractModel):
    schema_version: Literal[2]
    sources: list[SourceRecord] = Field(min_length=1)
    vehicles: list[VehicleIdentity] = Field(min_length=1)
    variants: list[VariantIdentity] = Field(min_length=1)
    snapshots: list[SourceSnapshot] = Field(min_length=1)
    observations: list[SpecObservation] = Field(default_factory=list)
    decisions: list[FactDecision] = Field(default_factory=list)

    @model_validator(mode="after")
    def references_and_identity(self) -> Self:
        sources = _index(self.sources, "source_key")
        vehicles = _index(self.vehicles, "canonical_key")
        variants = _index(self.variants, "variant_key")
        snapshots = _index(self.snapshots, "id")
        observations = _index(self.observations, "id")
        _index(self.decisions, "id")
        snapshot_acquisitions = set()
        for snapshot in self.snapshots:
            acquisition = (
                snapshot.source_key,
                str(snapshot.url),
                snapshot.retrieved_at,
                snapshot.content_sha256,
            )
            if acquisition in snapshot_acquisitions:
                raise ValueError("duplicate snapshot acquisition")
            snapshot_acquisitions.add(acquisition)
        identities = set()
        for vehicle in self.vehicles:
            identity = (
                vehicle.make.casefold(),
                vehicle.model.casefold(),
                vehicle.vehicle_type,
                vehicle.generation_key,
                vehicle.phase_key,
                vehicle.body_style,
                vehicle.model_year,
                vehicle.market,
            )
            if identity in identities:
                raise ValueError(
                    "duplicate vehicle identity, including unknown attributes"
                )
            identities.add(identity)
        for snapshot in self.snapshots:
            if snapshot.source_key not in sources:
                raise ValueError("snapshot references unknown source")
        for record in [*self.vehicles, *self.variants]:
            if not set(record.evidence_snapshot_ids) <= snapshots.keys():
                raise ValueError("identity references unknown snapshot")
        for variant in self.variants:
            if variant.vehicle_key not in vehicles:
                raise ValueError("variant references unknown vehicle")
        for observation in self.observations:
            if observation.snapshot_id not in snapshots:
                raise ValueError("observation references unknown snapshot")
            keys = observation.candidate_variant_keys
            if observation.variant_key:
                keys = [observation.variant_key]
            for key in keys:
                if key not in variants:
                    raise ValueError("observation references unknown variant")
                vehicle = vehicles[variants[key].vehicle_key]
                if observation.context.market != vehicle.market:
                    raise ValueError("observation market differs from variant market")
                if not variants[key].overlaps(observation.context):
                    raise ValueError(
                        "observation validity does not overlap its variant"
                    )
        seen_decisions: dict[UUID, FactDecision] = {}
        heads: dict[tuple, UUID] = {}
        for decision in self.decisions:
            if decision.variant_key not in variants:
                raise ValueError("decision references unknown variant")
            vehicle = vehicles[variants[decision.variant_key].vehicle_key]
            if decision.context.market != vehicle.market:
                raise ValueError("decision market differs from variant market")
            if not variants[decision.variant_key].overlaps(decision.context):
                raise ValueError("decision validity does not overlap its variant")
            scope = (
                decision.variant_key,
                decision.metric,
                decision.context.model_dump_json(),
            )
            if decision.supersedes_id != heads.get(scope):
                raise ValueError(
                    "decisions must form one ordered revision chain per fact"
                )
            if decision.supersedes_id:
                previous = seen_decisions[decision.supersedes_id]
                if decision.decided_at < previous.decided_at:
                    raise ValueError("decision revision predates previous decision")
            for evidence_id in decision.evidence_ids:
                observation = observations.get(evidence_id)
                if observation is None:
                    raise ValueError("decision references unknown observation")
                if (
                    observation.variant_key != decision.variant_key
                    or observation.metric != decision.metric
                    or observation.context != decision.context
                ):
                    raise ValueError(
                        "decision evidence has different identity/metric/context"
                    )
                if (
                    decision.decided_at
                    < snapshots[observation.snapshot_id].retrieved_at
                ):
                    raise ValueError("decision predates evidence acquisition")
            if decision.status == "verified" and decision.metric in MEASURED_METRICS:
                if decision.context.procedure in {
                    None,
                    "unknown",
                } or decision.context.cycle in {None, "unknown"}:
                    raise ValueError(
                        "cannot verify a measurement with unknown procedure/cycle"
                    )
                variant = variants[decision.variant_key]
                if (
                    variant.powertrain_type == "PHEV"
                    and decision.context.battery_condition in {None, "unknown"}
                ):
                    raise ValueError("PHEV measurement requires battery condition")
            seen_decisions[decision.id] = decision
            heads[scope] = decision.id
        return self


def load_catalog_v2(path: str | Path) -> CatalogV2:
    try:
        return CatalogV2.model_validate(
            json.loads(Path(path).read_text(), parse_float=Decimal)
        )
    except (OSError, UnicodeError) as error:
        raise CatalogValidationError("Cannot read catalog v2 file.") from error
    except json.JSONDecodeError as error:
        raise CatalogValidationError("Invalid catalog v2 JSON.") from error
    except ValidationError as error:
        # Never echo source content, URLs with credentials, or the whole payload.
        details = "; ".join(
            f"{'.'.join(map(str, item['loc'])) or 'catalog'}: {item['msg']}"
            for item in error.errors(include_input=False, include_url=False)
        )
        raise CatalogValidationError(details) from error
