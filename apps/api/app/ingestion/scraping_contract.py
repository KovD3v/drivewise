"""Operator-owned scope and agent proposals for the catalog collector."""

from datetime import date
import math
import re
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import Field, model_validator

from app.ingestion.catalog import SourceRecord
from app.ingestion.catalog_v2 import (
    ContractModel,
    Key,
    Market,
    METRIC_UNITS,
    MeasurementContext,
    Metric,
    Number,
    Text,
    VariantIdentity,
    VehicleIdentity,
)


def public_url(value: str) -> str:
    """Only exact, operator-approved HTTPS hosts; never credentials or local IPs."""
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or not host.isascii()
        or "." not in host
        or host.endswith((".local", ".localhost", ".internal", ".test"))
        or host.replace(".", "").isdigit()
        or ":" in host
        or "\\" in value
        or any(ord(c) < 33 for c in value)
    ):
        raise ValueError("a public HTTPS URL without credentials is required")
    return urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))


class TrustedSource(ContractModel):
    record: SourceRecord
    allowed_hosts: list[str] = Field(min_length=1, max_length=10)
    seed_urls: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def trusted_seeds(self):
        for host in self.allowed_hosts:
            if public_url(f"https://{host}/") != f"https://{host}/":
                raise ValueError("allowed_hosts must contain exact lowercase hosts")
        for url in [self.record.url, *self.seed_urls]:
            if urlsplit(public_url(url)).hostname not in self.allowed_hosts:
                raise ValueError("source and seed URLs must use allowed_hosts")
        return self


class CollectionTarget(ContractModel):
    model_family_key: Key
    make: Text
    model: Text
    market: Market = "IT"
    sold_from: date = date(2010, 1, 1)
    instructions: str = Field(default="", max_length=2000)
    metrics: list[Metric] = Field(min_length=1)


class RunLimits(ContractModel):
    max_model_calls: int = Field(default=24, ge=2, le=200)
    max_browser_calls: int = Field(default=12, ge=1, le=100)
    max_output_tokens: int = Field(default=8000, ge=256, le=32000)
    max_context_bytes: int = Field(default=240000, ge=20000, le=1000000)
    max_document_chars: int = Field(default=200000, ge=1000, le=1000000)


class ScrapingConfig(ContractModel):
    target: CollectionTarget
    sources: list[TrustedSource] = Field(min_length=1, max_length=20)
    limits: RunLimits = Field(default_factory=RunLimits)

    @model_validator(mode="after")
    def distinct_sources(self):
        keys = [s.record.source_key for s in self.sources]
        hosts = [host for s in self.sources for host in s.allowed_hosts]
        if len(set(keys)) != len(keys) or len(set(hosts)) != len(hosts):
            raise ValueError("source keys and allowed hosts must not overlap")
        return self

    def source_for(self, url: str) -> TrustedSource:
        host = urlsplit(public_url(url)).hostname
        for source in self.sources:
            if host in source.allowed_hosts:
                return source
        raise ValueError("URL is outside the configured trusted hosts")


class Browse(ContractModel):
    url: str = Field(max_length=2000)


class Discover(Browse):
    search: str = Field(min_length=1, max_length=200)


class ReadEvidence(ContractModel):
    snapshot_id: UUID
    start_line: int = Field(default=1, ge=1)


class ObservationProposal(ContractModel):
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
    evidence_excerpt: str = Field(min_length=1, max_length=4000)
    evidence_locator: Text

    @model_validator(mode="after")
    def checked_conversion(self):
        # Only unambiguous decimal scalars/ranges; grouped numbers require review.
        number = r"\d+(?:[.,]\d+)?"
        match = re.fullmatch(rf"({number})(?:\s*[-–]\s*({number}))?", self.raw_value)
        if not match:
            raise ValueError("raw_value must be a decimal scalar or ascending range")
        lower, upper = [
            float(v.replace(",", ".")) for v in (match[1], match[2] or match[1])
        ]
        if lower > upper:
            raise ValueError("raw range is inverted; investigate the source")
        target = METRIC_UNITS[self.metric]
        if self.unit != target:
            raise ValueError("normalized unit does not match the metric")
        raw_unit = (
            (self.raw_unit or "count").replace(" ", "").replace("³", "3").casefold()
        )
        conversions = {
            ("cv", "kW"): 0.73549875,
            ("ps", "kW"): 0.73549875,
            ("cc", "cm3"): 1,
            ("l", "cm3"): 1000,
            ("wh", "kWh"): 0.001,
            ("wh/km", "kWh/100km"): 0.1,
            ("m", "mm"): 1000,
            ("cm", "mm"): 10,
            ("dm3", "l"): 1,
            ("litri", "l"): 1,
        }
        if raw_unit == "km/l" and target == "l/100km":
            if lower == 0:
                raise ValueError("cannot convert zero km/l")
            lower, upper = 100 / upper, 100 / lower
        else:
            factor = (
                1
                if raw_unit == target.casefold()
                else conversions.get((raw_unit, target))
            )
            if factor is None:
                raise ValueError("unsupported unit conversion; retain a gap")
            lower, upper = lower * factor, upper * factor
        if not math.isclose(
            self.value_min, lower, rel_tol=1e-5, abs_tol=1e-5
        ) or not math.isclose(self.value_max, upper, rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError("normalized values differ from deterministic conversion")
        return self


class Extraction(ContractModel):
    vehicles: list[VehicleIdentity] = Field(min_length=1, max_length=30)
    variants: list[VariantIdentity] = Field(min_length=1, max_length=100)
    observations: list[ObservationProposal] = Field(max_length=1000)
    gaps: list[Text] = Field(default_factory=list, max_length=100)


class DecisionProposal(ContractModel):
    variant_key: Key
    metric: Metric
    context: MeasurementContext
    status: Literal["verified", "unknown", "not_applicable", "conflicted"]
    selected_observation_id: UUID | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    reason: Text


class Investigation(ContractModel):
    additional_observations: list[ObservationProposal] = Field(
        default_factory=list, max_length=1000
    )
    decisions: list[DecisionProposal] = Field(max_length=1000)
    gaps: list[Text] = Field(default_factory=list, max_length=100)


class NoEvidence(ContractModel):
    reason: Text
