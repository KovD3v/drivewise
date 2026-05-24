from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_advisor_repository,
    get_documents_repository,
    get_vehicles_repository,
)
from app.repositories.advisor import AdvisorRepository
from app.repositories.documents import DocumentsRepository
from app.repositories.vehicles import VehiclesRepository
from app.schemas.advisor import (
    AdvisorRecommendationRequest,
    AdvisorRecommendationResponse,
    ModelAnalysisRequest,
    ModelAnalysisResponse,
)
from app.services.advisor.document_evidence import attach_document_evidence
from app.services.advisor.model_analysis import build_model_analysis
from app.services.advisor.scoring import build_recommendations
from app.schemas.vehicles import VehicleResolveRequest
from app.services.vehicles.resolver import resolve_vehicle_query


router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.post("/recommendations", response_model=AdvisorRecommendationResponse)
def create_recommendations(
    request: AdvisorRecommendationRequest,
    repository: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    documents_repository: Annotated[
        DocumentsRepository,
        Depends(get_documents_repository),
    ],
) -> AdvisorRecommendationResponse:
    candidates = repository.list_candidates()
    items = build_recommendations(request, candidates)
    run_id = repository.create_run(request.model_dump(mode="json"))
    repository.save_items(run_id, items)
    repository.mark_run_completed(run_id)
    response_items = attach_document_evidence(items, documents_repository)

    return AdvisorRecommendationResponse(run_id=run_id, items=response_items)


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

    return build_model_analysis(
        request,
        advisor_repository.list_candidates(),
        resolve_response,
    )
