from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.advisor import AdvisorRecommendationRequest
from app.schemas.advisor import AdvisorGarageDimensions
from app.schemas.guided_decisions import (
    DecisionProfile,
    GarageCompatibility,
    GuidedDecisionResponse,
    PreviewRanking,
)
from app.services.advisor.scoring import (
    SCORING_VERSION,
    build_assumptions,
    score_recommendations,
)
from app.services.guided_decisions.garage import (
    VehicleDimensions,
    evaluate_garage_compatibility,
)
from app.services.guided_decisions.interpreter import extract_profile_updates
from app.services.guided_decisions.questions import (
    missing_information,
    next_question,
    profile_completion,
    weighted_fact_confidence,
)


@dataclass(frozen=True)
class GuidedDecisionEngineResult:
    profile: DecisionProfile
    response: GuidedDecisionResponse


def process_guided_decision_turn(
    *,
    decision_id: UUID,
    profile_version: int,
    current_profile: DecisionProfile,
    message: str,
    advisor_repository,
    as_of: datetime,
) -> GuidedDecisionEngineResult:
    previous_question = next_question(current_profile)
    profile, updated_fields = extract_profile_updates(
        message,
        current_profile,
        expected_question_id=previous_question.id if previous_question else None,
        captured_at=as_of,
    )

    preview_ranking, garage_compatibility = _build_preview_ranking(
        profile,
        advisor_repository=advisor_repository,
        as_of=as_of,
    )
    completion = profile_completion(profile)
    confidence = _decision_confidence(profile, preview_ranking)
    missing = missing_information(profile)
    question = next_question(profile)
    assistant_message = _assistant_message(profile, updated_fields, question)

    response = GuidedDecisionResponse(
        decision_id=decision_id,
        profile_version=profile_version,
        status="active",
        message=assistant_message,
        decision_profile=profile,
        updated_fields=updated_fields,
        profile_completion=completion,
        decision_confidence=confidence,
        missing_information=missing,
        next_question=question,
        preview_ranking=preview_ranking,
        garage_compatibility=garage_compatibility,
        warnings=_warnings(updated_fields),
    )
    return GuidedDecisionEngineResult(profile=profile, response=response)


def _build_preview_ranking(
    profile: DecisionProfile,
    *,
    advisor_repository,
    as_of: datetime,
) -> tuple[PreviewRanking, list[GarageCompatibility]]:
    blocking_reasons = []
    if profile.budget_eur is None:
        blocking_reasons.append("budget_eur")
    if profile.primary_use is None:
        blocking_reasons.append("primary_use")
    if blocking_reasons:
        return (
            PreviewRanking(
                status="blocked",
                blocking_reasons=blocking_reasons,
            ),
            [],
        )

    request = _advisor_request_from_profile(profile)
    candidates = advisor_repository.list_candidates(as_of=as_of)
    repository_exclusions = advisor_repository.count_excluded_candidates(as_of=as_of)
    result = score_recommendations(
        request,
        candidates,
        as_of=as_of,
        initial_excluded_counts=repository_exclusions,
    )
    has_items = any(group.items for group in result.groups)
    preview = PreviewRanking(
        status=(
            "ready"
            if has_items and all(
                item.decision_status == "complete"
                for group in result.groups
                for item in group.items
            )
            else "provisional"
            if has_items
            else "insufficient_inventory"
        ),
        scoring_version=SCORING_VERSION,
        assumptions=build_assumptions(request),
        groups=result.groups,
    )
    return preview, _garage_compatibility(profile, result.groups, candidates)


def _advisor_request_from_profile(profile: DecisionProfile) -> AdvisorRecommendationRequest:
    garage_values = {
        field_name: getattr(profile.garage, field_name).value
        for field_name in (
            "useful_length_mm",
            "useful_width_mm",
            "useful_height_mm",
            "door_width_mm",
            "door_height_mm",
        )
        if getattr(profile.garage, field_name) is not None
    }
    garage = (
        AdvisorGarageDimensions.model_validate(garage_values)
        if len(garage_values) == 5
        else None
    )
    return AdvisorRecommendationRequest(
        budget_max_eur=profile.budget_eur.value,
        primary_use=profile.primary_use.value,
        usage=profile.usage.value if profile.usage else None,
        children_count=(
            profile.children_count.value if profile.children_count else None
        ),
        passengers_usual=(
            profile.passengers_usual.value if profile.passengers_usual else None
        ),
        garage=garage,
        automatic_required=(
            profile.automatic_required.value
            if profile.automatic_required
            else None
        ),
        constraint_modes=profile.constraint_modes,
        condition=profile.condition.value if profile.condition else "any",
        annual_km=profile.annual_km.value if profile.annual_km else None,
        preferred_fuel_type=(
            profile.preferred_fuel_type.value if profile.preferred_fuel_type else None
        ),
        preferred_body_style=profile.category.value if profile.category else None,
        max_mileage=(profile.max_mileage_km.value if profile.max_mileage_km else None),
        priorities=profile.priorities.value if profile.priorities else [],
    )


def _garage_compatibility(
    profile: DecisionProfile,
    groups,
    candidates: list[dict[str, Any]],
) -> list[GarageCompatibility]:
    if profile.parking is None or profile.parking.value != "garage":
        return []

    dimensions_by_spec = {
        candidate["spec"]["id"]: VehicleDimensions(
            length_mm=candidate["spec"].get("length_mm"),
            body_width_mm=candidate["spec"].get("body_width_mm"),
            height_mm=candidate["spec"].get("height_mm"),
            entry_width_mm=candidate["spec"].get("width_mirrors_folded_mm"),
        )
        for candidate in candidates
    }
    checks: list[GarageCompatibility] = []
    for group in groups:
        for item in group.items:
            dimensions = dimensions_by_spec.get(
                item.selected_spec.id,
                VehicleDimensions(None, None, None, None),
            )
            check = evaluate_garage_compatibility(
                profile,
                vehicle_id=item.vehicle.id,
                spec_id=item.selected_spec.id,
                vehicle_dimensions=dimensions,
            )
            if check is not None:
                checks.append(check)
    return checks


def _decision_confidence(
    profile: DecisionProfile,
    preview_ranking: PreviewRanking,
) -> float:
    profile_signal = weighted_fact_confidence(profile)
    if preview_ranking.status == "provisional":
        ranking_signal = max(
            (
                item.decision_confidence or 0.0
                for group in preview_ranking.groups
                for item in group.items
            ),
            default=0.0,
        ) / 100
        ranking_signal = max(0.0, min(1.0, ranking_signal))
    else:
        ranking_signal = {
            "blocked": 0.0,
            "insufficient_inventory": 0.15,
            "ready": 0.70,
        }[preview_ranking.status]
    return round(0.85 * profile_signal + 0.15 * ranking_signal, 2)


def _assistant_message(profile, updated_fields: list[str], question) -> str:
    if updated_fields:
        summary = _profile_summary(profile, updated_fields)
        opening = f"Perfetto, ho aggiornato il profilo: {summary}."
    else:
        opening = "Non ho ricavato nuovi dati con sufficiente affidabilità."
    if question is None:
        return f"{opening} Il profilo contiene già le informazioni previste."
    return f"{opening} {question.label}"


def _profile_summary(profile: DecisionProfile, updated_fields: list[str]) -> str:
    parts = []
    if "category" in updated_fields and profile.category:
        parts.append(f"categoria {profile.category.value}")
    if "primary_use" in updated_fields and profile.primary_use:
        parts.append(f"uso principale {profile.primary_use.value}")
    if "budget_eur" in updated_fields and profile.budget_eur:
        amount = f"{profile.budget_eur.value:,.0f}".replace(",", ".")
        parts.append(f"budget circa {amount} EUR")
    if "annual_km" in updated_fields and profile.annual_km:
        parts.append(f"{profile.annual_km.value:,} km annui".replace(",", "."))
    if "parking" in updated_fields and profile.parking:
        parts.append(f"parcheggio {profile.parking.value}")
    if not parts:
        parts.append(", ".join(updated_fields))
    return ", ".join(parts)


def _warnings(updated_fields: list[str]) -> list[str]:
    if updated_fields:
        return []
    return [
        "Il messaggio non ha prodotto aggiornamenti automatici; il profilo precedente è stato conservato."
    ]
