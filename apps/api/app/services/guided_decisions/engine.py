from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError

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
from app.services.guided_decisions.interpreter import (
    extract_profile_updates,
    is_non_positive_garage_dimension,
)
from app.services.guided_decisions.questions import (
    missing_information,
    next_question,
    profile_completion,
    weighted_fact_confidence,
)


# Every turn rewrites the stored profile and appends a turn row; the cap bounds
# what one anonymous decision link can write. Creation counts as turn one.
MAX_GUIDED_DECISION_TURNS = 40

GARAGE_DIMENSION_FIELDS = (
    "useful_length_mm",
    "useful_width_mm",
    "useful_height_mm",
    "door_width_mm",
    "door_height_mm",
)

RECOMPUTE_FALLBACK_WARNING = (
    "Non è stato possibile ricalcolare la classifica con il catalogo attuale: "
    "mostriamo l'ultima risposta salvata, che potrebbe non essere aggiornata."
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

    live = _live_fields(profile, advisor_repository=advisor_repository, as_of=as_of)
    assistant_message = _assistant_message(
        profile, updated_fields, live["next_question"]
    )

    response = GuidedDecisionResponse(
        decision_id=decision_id,
        profile_version=profile_version,
        status="active",
        message=assistant_message,
        decision_profile=profile,
        updated_fields=updated_fields,
        **live,
        warnings=_warnings(
            updated_fields,
            invalid_garage_dimension=(
                previous_question is not None
                and previous_question.id.startswith("garage.")
                and is_non_positive_garage_dimension(message)
            ),
        ),
    )
    return GuidedDecisionEngineResult(profile=profile, response=response)


def recompute_guided_decision_response(
    stored: GuidedDecisionResponse,
    profile: DecisionProfile,
    *,
    advisor_repository,
    as_of: datetime,
) -> GuidedDecisionResponse:
    """Rebuild the ranking of a stored decision from its profile.

    A reopened link must reflect the current catalogue and source permissions,
    so a revoked source never lingers in a saved answer. Only a profile that
    today's validation rejects falls back to the stored answer, with a warning;
    any other failure propagates instead of serving stale data silently.
    """
    # Only the profile-to-request step may fall back: a validation error raised
    # by catalogue data must surface, never hide behind the stored answer.
    try:
        if profile.budget_eur is not None and profile.primary_use is not None:
            _advisor_request_from_profile(profile)
    except ValidationError:
        warnings = list(dict.fromkeys([*stored.warnings, RECOMPUTE_FALLBACK_WARNING]))
        return stored.model_copy(update={"warnings": warnings})
    live = _live_fields(profile, advisor_repository=advisor_repository, as_of=as_of)
    return stored.model_copy(update={"decision_profile": profile, **live})


def _live_fields(
    profile: DecisionProfile,
    *,
    advisor_repository,
    as_of: datetime,
) -> dict[str, Any]:
    preview_ranking, garage_compatibility = _build_preview_ranking(
        profile,
        advisor_repository=advisor_repository,
        as_of=as_of,
    )
    return {
        "profile_completion": profile_completion(profile),
        "decision_confidence": _decision_confidence(profile, preview_ranking),
        "missing_information": missing_information(profile),
        "next_question": next_question(profile),
        "preview_ranking": preview_ranking,
        "garage_compatibility": garage_compatibility,
    }


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
    result = score_recommendations(
        request,
        candidates,
        as_of=as_of,
        pending_garage=_pending_hard_garage(profile),
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


def _garage_values(profile: DecisionProfile) -> dict[str, int]:
    return {
        field_name: getattr(profile.garage, field_name).value
        for field_name in GARAGE_DIMENSION_FIELDS
        if getattr(profile.garage, field_name) is not None
    }


def _parks_in_garage(profile: DecisionProfile) -> bool:
    return profile.parking is not None and profile.parking.value == "garage"


def _pending_hard_garage(profile: DecisionProfile) -> dict[str, int] | None:
    """Known garage measures while a hard garage constraint is still incomplete.

    Without them the Advisor request carries no garage at all, so the hard
    constraint would vanish and the preview could report ``ready``.
    """
    garage_values = _garage_values(profile)
    if (
        _parks_in_garage(profile)
        and profile.constraint_modes.garage == "hard"
        and len(garage_values) < len(GARAGE_DIMENSION_FIELDS)
    ):
        return garage_values
    return None


def _advisor_request_from_profile(profile: DecisionProfile) -> AdvisorRecommendationRequest:
    garage_values = _garage_values(profile)
    garage = (
        AdvisorGarageDimensions.model_validate(garage_values)
        if _parks_in_garage(profile)
        and len(garage_values) == len(GARAGE_DIMENSION_FIELDS)
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

    dimensions_by_spec = {}
    for candidate in candidates:
        dimensions = (candidate.get("decision_context") or {}).get(
            "dimensions"
        ) or {}
        dimensions_by_spec[candidate["spec"]["id"]] = VehicleDimensions(
            length_mm=dimensions.get("length_mm"),
            body_width_mm=dimensions.get("body_width_mm"),
            height_mm=dimensions.get("height_mm"),
            entry_width_mm=dimensions.get("width_mirrors_folded_mm"),
        )
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


_READY_RANKING_SIGNAL = 0.70


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
        # A provisional ranking never signals more than a ready one.
        ranking_signal = max(0.0, min(_READY_RANKING_SIGNAL, ranking_signal))
    else:
        ranking_signal = {
            "blocked": 0.0,
            "insufficient_inventory": 0.15,
            "ready": _READY_RANKING_SIGNAL,
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


def _warnings(
    updated_fields: list[str], *, invalid_garage_dimension: bool = False
) -> list[str]:
    if invalid_garage_dimension:
        return ["garage_dimension_must_be_positive"]
    if updated_fields:
        return []
    return [
        "Il messaggio non ha prodotto aggiornamenti automatici; il profilo precedente è stato conservato."
    ]
