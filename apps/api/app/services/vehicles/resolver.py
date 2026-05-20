from dataclasses import dataclass
from typing import Any
import unicodedata

from app.schemas.vehicles import (
    VehicleResolveMatch,
    VehicleResolveRequest,
    VehicleResolveResponse,
    VehicleSpec,
    VehicleSummary,
)


MATCHED_CONFIDENCE = 0.82
AMBIGUOUS_CONFIDENCE = 0.65
MATCHED_MARGIN = 0.08
TRIM_COMMON_TOKENS = {
    "hybrid",
    "petrol",
    "diesel",
    "electric",
    "mild",
    "full",
    "turbo",
}


@dataclass(frozen=True)
class ScoredCandidate:
    confidence: float
    matched_fields: list[str]
    warnings: list[str]
    vehicle: VehicleSummary
    spec: VehicleSpec | None

    @property
    def match_level(self) -> str:
        if self.spec is not None and "trim" in self.matched_fields:
            return "spec"
        return "vehicle"


def normalize_query_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    chars = [
        char.lower() if char.isalnum() else " "
        for char in without_accents
    ]
    return " ".join("".join(chars).split())


def resolve_vehicle_query(
    request: VehicleResolveRequest,
    rows: list[dict[str, Any]],
) -> VehicleResolveResponse:
    normalized_query = normalize_query_text(request.query)
    query_tokens = set(normalized_query.split())

    candidates = [
        _score_candidate(request, normalized_query, query_tokens, row)
        for row in rows
    ]
    candidates.sort(
        key=lambda candidate: (
            -candidate.confidence,
            candidate.vehicle.make,
            candidate.vehicle.model,
            candidate.vehicle.model_year,
            candidate.spec.trim if candidate.spec else "",
        )
    )

    eligible_candidates = [
        candidate
        for candidate in candidates
        if candidate.confidence >= AMBIGUOUS_CONFIDENCE
    ]

    status = _resolve_status(eligible_candidates)
    eligible = eligible_candidates[: request.limit]
    if status == "no_match":
        eligible = []

    return VehicleResolveResponse(
        query=request.query,
        normalized_query=normalized_query,
        status=status,
        matches=[
            VehicleResolveMatch(
                confidence=round(candidate.confidence, 2),
                match_level=candidate.match_level,
                vehicle=candidate.vehicle,
                spec=candidate.spec,
                matched_fields=candidate.matched_fields,
                warnings=candidate.warnings,
            )
            for candidate in eligible
        ],
    )


def _score_candidate(
    request: VehicleResolveRequest,
    normalized_query: str,
    query_tokens: set[str],
    row: dict[str, Any],
) -> ScoredCandidate:
    score = 0.0
    matched_fields: list[str] = []
    warnings: list[str] = []

    if _all_tokens_match(row["make"], normalized_query, query_tokens):
        score += 0.18
        matched_fields.append("make")

    model_score = _model_overlap(row["model"], query_tokens)
    if model_score > 0:
        score += 0.32 * model_score
        matched_fields.append("model")

    if _matches_model_year(request, row, query_tokens):
        score += 0.12
        matched_fields.append("model_year")

    spec = _row_to_spec(row)
    if spec is None:
        warnings.append("no_spec_match")
    else:
        trim_score = _trim_overlap(spec.trim, query_tokens)
        if trim_score > 0:
            score += 0.26 * trim_score
            matched_fields.append("trim")

    if request.fuel_type and request.fuel_type == row["fuel_type"]:
        score += 0.08
        matched_fields.append("fuel_type")

    if request.body_style and request.body_style == row["body_style"]:
        score += 0.04
        matched_fields.append("body_style")

    if "model" in matched_fields and "trim" in matched_fields:
        if "make" in matched_fields:
            score += 0.17
        else:
            score += 0.26

    return ScoredCandidate(
        confidence=min(score, 1.0),
        matched_fields=matched_fields,
        warnings=warnings,
        vehicle=VehicleSummary.model_validate(row),
        spec=spec,
    )


def _resolve_status(candidates: list[ScoredCandidate]) -> str:
    if not candidates:
        return "no_match"

    first = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None
    margin = first.confidence - second.confidence if second else 1.0
    if first.confidence >= MATCHED_CONFIDENCE and margin >= MATCHED_MARGIN:
        return "matched"
    return "ambiguous"


def _all_tokens_match(
    value: str,
    normalized_query: str,
    query_tokens: set[str],
) -> bool:
    normalized_value = normalize_query_text(value)
    value_tokens = set(normalized_value.split())
    return normalized_value in normalized_query or value_tokens <= query_tokens


def _token_overlap(value: str | None, query_tokens: set[str]) -> float:
    if not value:
        return 0.0
    value_tokens = set(normalize_query_text(value).split())
    if not value_tokens:
        return 0.0
    return len(value_tokens & query_tokens) / len(value_tokens)


def _model_overlap(value: str, query_tokens: set[str]) -> float:
    model_tokens = normalize_query_text(value).split()
    if not model_tokens:
        return 0.0
    overlap = len(set(model_tokens) & query_tokens) / len(model_tokens)
    if overlap == 1.0:
        return 1.0
    if model_tokens[0] in query_tokens:
        return max(overlap, 0.85)
    return overlap


def _trim_overlap(value: str, query_tokens: set[str]) -> float:
    trim_tokens = normalize_query_text(value).split()
    if not trim_tokens:
        return 0.0
    overlap = len(set(trim_tokens) & query_tokens) / len(trim_tokens)
    if overlap == 1.0:
        return 1.0

    distinctive_tokens = [
        token
        for token in trim_tokens
        if len(token) >= 4 and token not in TRIM_COMMON_TOKENS
    ]
    if any(token in query_tokens for token in distinctive_tokens):
        return max(overlap, 0.85)

    return overlap


def _matches_model_year(
    request: VehicleResolveRequest,
    row: dict[str, Any],
    query_tokens: set[str],
) -> bool:
    model_year = str(row["model_year"])
    return request.model_year == row["model_year"] or model_year in query_tokens


def _row_to_spec(row: dict[str, Any]) -> VehicleSpec | None:
    if row.get("spec_id") is None:
        return None
    return VehicleSpec.model_validate(
        {
            "id": row["spec_id"],
            "trim": row["trim"],
            "drivetrain": row["drivetrain"],
            "transmission": row["transmission"],
            "engine": row["engine"],
            "horsepower": row["horsepower"],
            "battery_kwh": row["battery_kwh"],
            "consumption_l_100km": row["consumption_l_100km"],
            "wltp_range_km": row["wltp_range_km"],
            "co2_g_km": row["co2_g_km"],
            "euro_emission_standard": row["euro_emission_standard"],
            "seats": row["seats"],
            "cargo_volume_liters": row["cargo_volume_liters"],
        }
    )
