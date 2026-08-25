from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_advisor_repository,
    get_vehicles_repository,
)
from app.repositories.advisor import AdvisorRepository
from app.repositories.vehicles import VehiclesRepository
from app.schemas.advisor import (
    AdvisorRecommendationRequest,
    AdvisorRecommendationResponse,
    ModelAnalysisRequest,
    ModelAnalysisResponse,
)
from app.services.advisor.model_analysis import build_model_analysis
from app.services.advisor.scoring import (
    ACTIVE_MODULE_VERSIONS,
    SCORING_VERSION,
    build_assumptions,
    score_recommendations,
)
from app.services.advisor.confidence import CONFIDENCE_VERSION
from app.schemas.vehicles import VehicleResolveRequest
from app.services.vehicles.resolver import resolve_vehicle_query


router = APIRouter(prefix="/advisor", tags=["advisor"])


def get_advisor_clock() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/recommendations", response_model=AdvisorRecommendationResponse)
def create_recommendations(
    request: AdvisorRecommendationRequest,
    repository: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    as_of: Annotated[datetime, Depends(get_advisor_clock)],
) -> AdvisorRecommendationResponse:
    candidates = repository.list_candidates(as_of=as_of)
    repository_exclusions = repository.count_excluded_candidates(as_of=as_of)
    result = score_recommendations(
        request,
        candidates,
        as_of=as_of,
        initial_excluded_counts=repository_exclusions,
    )
    assumptions = build_assumptions(request)
    normalized_profile = request.model_dump(mode="json")
    actual_modules = {
        name: version
        for item in result.items
        for name, version in item.module_versions.items()
    }
    active_modules = {**ACTIVE_MODULE_VERSIONS, **actual_modules}
    active_versions = {
        "scoring": SCORING_VERSION,
        "confidence": CONFIDENCE_VERSION,
        "modules": dict(sorted(active_modules.items())),
    }
    request_payload = {
        **normalized_profile,
        "normalized_profile": normalized_profile,
        "active_versions": active_versions,
    }
    request_payload["scoring_version"] = SCORING_VERSION
    request_payload["evaluated_at"] = as_of.isoformat()
    request_payload["annual_km_defaulted"] = request.annual_km_was_defaulted
    run_id = repository.create_run(
        request_payload,
        scoring_version=SCORING_VERSION,
        assumptions=assumptions,
        exclusion_counts=result.excluded_counts_by_reason,
    )
    repository.save_items(run_id, result.groups)
    repository.mark_run_completed(run_id)

    return AdvisorRecommendationResponse(
        run_id=run_id,
        scoring_version=SCORING_VERSION,
        assumptions=assumptions,
        excluded_counts_by_reason=result.excluded_counts_by_reason,
        groups=result.groups,
    )


@router.post("/model-analysis", response_model=ModelAnalysisResponse)
def create_model_analysis(
    request: ModelAnalysisRequest,
    advisor_repository: Annotated[
        AdvisorRepository,
        Depends(get_advisor_repository),
    ],
    vehicles_repository: Annotated[
        VehiclesRepository,
        Depends(get_vehicles_repository),
    ],
    as_of: Annotated[datetime, Depends(get_advisor_clock)],
) -> ModelAnalysisResponse:
    resolve_response = None
    if request.vehicle_id is None and request.query is not None:
        resolve_request = VehicleResolveRequest(
            query=request.query,
            market=request.market,
            model_year=request.model_year,
            fuel_type=request.fuel_type,
            body_style=request.body_style,
        )
        resolve_response = resolve_vehicle_query(
            resolve_request,
            vehicles_repository.list_resolve_candidates(resolve_request.market),
        )

    list_model_candidates = getattr(
        advisor_repository,
        "list_model_analysis_candidates",
        advisor_repository.list_candidates,
    )
    return build_model_analysis(
        request,
        list_model_candidates(),
        resolve_response,
        as_of=as_of,
    )
